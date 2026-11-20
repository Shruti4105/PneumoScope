"""Small python-docx toolkit that follows the BTech AI/ML report formatting rules
(A4, Times New Roman 12 pt, 1.5 spacing, justified, 1-inch margins, 16/14 pt headings,
figure captions below, table captions above, numbered equations)."""
import re
import shutil
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

FONT = "Times New Roman"
TEXT_W = 6.27  # inches (A4 8.27 - 2 x 1)


def _strip_theme(style):
    rpr = style.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts"); rpr.append(rf)
    for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rf.attrib.pop(qn(a), None)
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), FONT)


def shade(cell, hexcol):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hexcol)
    tcPr.append(s)


def add_field(par, instr, placeholder=" "):
    def fc(t):
        r = par.add_run(); e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), t); r._r.append(e); return r
    fc("begin")
    r = par.add_run(); it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr; r._r.append(it)
    fc("separate"); par.add_run(placeholder); fc("end")


class Report:
    def __init__(self, figdir: Path):
        self.d = Document()
        self.fig = figdir
        self.ch = 0; self.nf = 0; self.nt = 0; self.ne = 0
        self.figs, self.tabs = [], []
        d = self.d
        sec = d.sections[0]
        sec.page_width, sec.page_height = Inches(8.27), Inches(11.69)
        for m in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
            setattr(sec, m, Inches(1))
        st = d.styles
        n = st["Normal"]; _strip_theme(n); n.font.name = FONT; n.font.size = Pt(12)
        pf = n.paragraph_format; pf.line_spacing = 1.5; pf.space_after = Pt(6); pf.space_before = Pt(0)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for name, size, before, after in (("Heading 1", 16, 0, 18), ("Heading 2", 14, 14, 6), ("Heading 3", 12, 10, 4)):
            h = st[name]; _strip_theme(h)
            h.font.size = Pt(size); h.font.bold = True; h.font.italic = False; h.font.color.rgb = RGBColor(0, 0, 0)
            h.paragraph_format.space_before = Pt(before); h.paragraph_format.space_after = Pt(after)
            h.paragraph_format.keep_with_next = True; h.paragraph_format.line_spacing = 1.15
            h.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
        st["Heading 1"].paragraph_format.page_break_before = True
        st["Heading 1"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for nm in ("Figure Caption", "Table Caption"):
            c = st.add_style(nm, 1); c.base_style = n
            c.font.size = Pt(11); c.font.bold = False
            c.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            c.paragraph_format.line_spacing = 1.0
            c.paragraph_format.space_before = Pt(4 if nm == "Figure Caption" else 10)
            c.paragraph_format.space_after = Pt(12 if nm == "Figure Caption" else 4)
            if nm == "Table Caption": c.paragraph_format.keep_with_next = True
        for nm in ("List Bullet", "List Number"):
            _strip_theme(st[nm]); st[nm].font.size = Pt(12); st[nm].paragraph_format.space_after = Pt(2)
        cc = st.add_style("Code Caption", 1); cc.base_style = n
        cc.font.size = Pt(10.5); cc.font.italic = True
        cc.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER; cc.paragraph_format.line_spacing = 1.0
        cc.paragraph_format.space_before = Pt(3); cc.paragraph_format.space_after = Pt(10)
        for nm in ("TOC 1", "TOC 2", "TOC 3"):
            try: ts = st[nm]
            except KeyError: ts = st.add_style(nm, 1)
            ts.base_style = n; ts.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            ts.paragraph_format.line_spacing = 1.15; ts.paragraph_format.space_after = Pt(3)
            if nm == "TOC 2": ts.paragraph_format.left_indent = Inches(0.3)
        co = st.add_style("CodeBlock", 1); co.base_style = n; _strip_theme(co)
        co.font.name = "Courier New"
        rpr = co.element.get_or_add_rPr(); rf = rpr.find(qn("w:rFonts"))
        for a in ("w:ascii", "w:hAnsi", "w:cs"): rf.set(qn(a), "Courier New")
        co.font.size = Pt(9); co.paragraph_format.line_spacing = 1.0; co.paragraph_format.space_after = Pt(0)
        co.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # ------------------------------------------------------------ inline markup: **bold**, *italic*, `code`
    def runs(self, par, text, size=None):
        for tok in re.split(r"(\*\*.+?\*\*|\*[^*\s][^*]*?\*|`[^`]+`|_\{[^}]*\}|\^\{[^}]*\})", text):
            if not tok: continue
            if tok.startswith("_{"): r = par.add_run(tok[2:-1]); r.font.subscript = True
            elif tok.startswith("^{"): r = par.add_run(tok[2:-1]); r.font.superscript = True
            elif tok.startswith("**"): r = par.add_run(tok[2:-2]); r.bold = True
            elif tok.startswith("`"):
                r = par.add_run(tok[1:-1]); r.font.name = "Courier New"; r.font.size = Pt(10.5)
            elif tok.startswith("*") and len(tok) > 2: r = par.add_run(tok[1:-1]); r.italic = True
            else: r = par.add_run(tok)
            if size and not tok.startswith("`"): r.font.size = Pt(size)
        return par

    def P(self, text, align=None, size=None, bold=False, space_after=None, italic=False):
        p = self.d.add_paragraph(); self.runs(p, text, size)
        if bold or italic:
            for r in p.runs: r.bold = r.bold or bold; r.italic = r.italic or italic
        if align == "c": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if align == "l": p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        if space_after is not None: p.paragraph_format.space_after = Pt(space_after)
        return p

    def B(self, items, numbered=False):
        for it in items:
            p = self.d.add_paragraph(style="List Number" if numbered else "List Bullet"); self.runs(p, it)
            p.paragraph_format.line_spacing = 1.3

    def H1(self, title, chapter=True, toc=True):
        if chapter:
            self.ch += 1; self.nf = self.nt = self.ne = 0
            text = f"CHAPTER {self.ch} — {title.upper()}"
        else:
            text = title.upper()
        p = self.d.add_paragraph(text, style="Heading 1" if toc else None)
        if not toc:
            p.paragraph_format.page_break_before = True; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs: r.bold = True; r.font.size = Pt(16)
            p.paragraph_format.space_after = Pt(18)
        return p

    def mapped(self, text):
        p = self.P(f"*Mapped to: {text}*", align="c"); p.paragraph_format.space_after = Pt(12)

    def H2(self, title): return self.d.add_paragraph(title, style="Heading 2")
    def H3(self, title): return self.d.add_paragraph(title, style="Heading 3")

    def FIG(self, name, caption, w=6.0, src=None):
        self.nf += 1; num = f"{self.ch}.{self.nf}"
        path = Path(src) if src else self.fig / name
        p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True; p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_before = Pt(6); p.paragraph_format.space_after = Pt(0)
        p.add_run().add_picture(str(path), width=Inches(min(w, TEXT_W)))
        c = self.d.add_paragraph(style="Figure Caption"); r = c.add_run(f"Figure {num}: "); r.bold = True
        self.runs(c, caption)
        self.figs.append((num, caption)); return f"Figure {num}"

    def next_fig(self): return f"Figure {self.ch}.{self.nf + 1}"
    def next_tab(self): return f"Table {self.ch}.{self.nt + 1}"
    def next_eq(self): return f"Eq. ({self.ch}.{self.ne + 1})"

    def TBL(self, header, rows, caption, widths=None, size=10, first_bold=False, align=None):
        num = None
        if caption:
            self.nt += 1; num = f"{self.ch}.{self.nt}"
            c = self.d.add_paragraph(style="Table Caption"); r = c.add_run(f"Table {num}: "); r.bold = True
            self.runs(c, caption)
            self.tabs.append((num, caption))
        ncol = len(header)
        widths = widths or [TEXT_W / ncol] * ncol
        s = sum(widths); widths = [w * TEXT_W / s for w in widths] if s > TEXT_W else widths
        t = self.d.add_table(rows=1 + len(rows), cols=ncol); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        for i, row in enumerate([header] + rows):
            for j, val in enumerate(row):
                cell = t.cell(i, j); cell.width = Inches(widths[j])
                p = cell.paragraphs[0]; p.paragraph_format.line_spacing = 1.0; p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.space_before = Pt(1)
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if (align is None or align[j] == "l") else WD_ALIGN_PARAGRAPH.CENTER
                self.runs(p, str(val), size)
                if i == 0:
                    shade(cell, "F3D9CC")
                    for rr in p.runs: rr.bold = True
                elif first_bold and j == 0:
                    for rr in p.runs: rr.bold = True
        if len(rows) <= 16:
            for row in t.rows[:-1]:
                for cell in row.cells:
                    for p in cell.paragraphs: p.paragraph_format.keep_with_next = True
        for row in t.rows:
            trPr0 = row._tr.get_or_add_trPr(); cs = OxmlElement("w:cantSplit"); cs.set(qn("w:val"), "true"); trPr0.append(cs)
        # repeat header row across pages
        trPr = t.rows[0]._tr.get_or_add_trPr(); h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); trPr.append(h)
        sp = self.d.add_paragraph(); sp.paragraph_format.space_after = Pt(4); sp.paragraph_format.line_spacing = 1.0
        return f"Table {num}"

    def EQ(self, parts):
        """parts: list of (text, kind) where kind in '', 'i' italic, 'sub', 'sup'.  Or a plain string with _{} and ^{}."""
        self.ne += 1; num = f"{self.ch}.{self.ne}"
        p = self.d.add_paragraph(); p.paragraph_format.line_spacing = 1.2
        p.paragraph_format.tab_stops.add_tab_stop(Inches(TEXT_W / 2), WD_TAB_ALIGNMENT.CENTER)
        p.paragraph_format.tab_stops.add_tab_stop(Inches(TEXT_W), WD_TAB_ALIGNMENT.RIGHT)
        p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(8)
        p.add_run("\t")
        for tok in re.split(r"(_\{[^}]*\}|\^\{[^}]*\})", parts):
            if not tok: continue
            if tok.startswith("_{"): r = p.add_run(tok[2:-1]); r.font.subscript = True
            elif tok.startswith("^{"): r = p.add_run(tok[2:-1]); r.font.superscript = True
            else: r = p.add_run(tok)
            r.italic = True; r.font.name = "Cambria Math"
            r._r.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), "Cambria Math")
        p.add_run(f"\t({num})")
        return f"Eq. ({num})"

    def CODE(self, text, caption=None):
        lines = text.strip("\n").splitlines()
        t = self.d.add_table(rows=1, cols=1); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = t.cell(0, 0); cell.width = Inches(TEXT_W); shade(cell, "F5F5F5")
        cell.paragraphs[0].style = self.d.styles["CodeBlock"]; cell.paragraphs[0].add_run(lines[0])
        trPr0 = t.rows[0]._tr.get_or_add_trPr(); cs = OxmlElement("w:cantSplit"); cs.set(qn("w:val"), "true"); trPr0.append(cs)
        for ln in lines[1:]:
            cp = cell.add_paragraph(style="CodeBlock"); cp.add_run(ln)
        if caption:
            c = self.d.add_paragraph(style="Code Caption"); self.runs(c, caption)
        else:
            sp = self.d.add_paragraph(); sp.paragraph_format.space_after = Pt(2); sp.paragraph_format.line_spacing = 1.0

    def MATH(self, title, concept, eq, notation, impl, result, interp, decision):
        """Part B structure: concept, expression, notation, implementation, results, interpretation, decision."""
        self.H3(title)
        self.P(f"**Concept.** {concept}")
        ref = None
        for e in ([eq] if isinstance(eq, str) else eq):
            r = self.EQ(e); ref = ref or r
        self.P(f"**Notation.** {notation}")
        self.P(f"**Implementation.** {impl}", align="l")
        self.P(f"**Result.** {result}")
        self.P(f"**Interpretation.** {interp}")
        self.P(f"**Decision.** {decision}")
        return ref

    def page_break(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def new_section(self, fmt, start=1, footer=True):
        sec = self.d.add_section(WD_SECTION.NEW_PAGE)
        sp = sec._sectPr
        pg = OxmlElement("w:pgNumType"); pg.set(qn("w:fmt"), fmt); pg.set(qn("w:start"), str(start))
        cols = sp.find(qn("w:cols"))
        (cols.addprevious(pg) if cols is not None else sp.append(pg))
        sec.footer.is_linked_to_previous = False
        fp = sec.footer.paragraphs[0]; fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in list(fp.runs): r._r.getparent().remove(r._r)
        if footer:
            add_field(fp, "PAGE", "1")
            for r in fp.runs: r.font.size = Pt(11); r.font.name = FONT
        return sec

    def toc(self, instr):
        p = self.d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        add_field(p, instr, "Right-click and choose Update Field.")

    def save(self, path): self.d.save(path)
