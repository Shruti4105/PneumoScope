import { Activity, Brain, Eye, HelpCircle, LineChart as LineIcon, ScanLine, Stethoscope, Wind } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Area, AreaChart, Bar, BarChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { axisProps, C, tooltipProps } from "../components/charts/theme";
import { cx, DecisionBadge, ErrorBox, Loading, PredictionBadge } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import { dateTime, pct } from "../utils/format";

/** Rounded icon tile used in card headers (like the reference). */
function IconTile({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "orange" | "rose" }) {
  const t = {
    neutral: "from-white/25 to-white/5",
    orange: "from-[#F9A26C] to-[#B84A20]",
    rose: "from-[#FCA5A5] to-[#9F3B3B]",
  }[tone];
  return <span className={cx("flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br text-white shadow-inner", t)}>{children}</span>;
}

function CardHead({ icon, title, note }: { icon: ReactNode; title: string; note?: string }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div className="flex items-center gap-3">{icon}<span className="text-[18px] font-medium text-ink">{title}</span></div>
      {note && <span className="text-[12px] text-muted">{note}</span>}
    </div>
  );
}

/** Semicircle gauge with tick marks (reference: speed gauge). */
function Gauge({ value }: { value: number }) {
  const ticks = 40;
  const cx0 = 150, cy0 = 150, r1 = 118, r2 = 132;
  return (
    <svg viewBox="0 0 300 170" className="w-full" role="img" aria-label={`Test accuracy ${pct(value)}`}>
      {Array.from({ length: ticks + 1 }, (_, i) => {
        const a = Math.PI * (1 - i / ticks);
        const on = i / ticks <= value;
        return (
          <line key={i} x1={cx0 + r1 * Math.cos(a)} y1={cy0 - r1 * Math.sin(a)} x2={cx0 + r2 * Math.cos(a)} y2={cy0 - r2 * Math.sin(a)}
            stroke={on ? "#F5F2EE" : "rgba(255,255,255,0.18)"} strokeWidth={i % 5 === 0 ? 3 : 2} strokeLinecap="round" />
        );
      })}
      <line x1={cx0} y1={cy0 - 108} x2={cx0} y2={cy0 - 86} stroke="#F5F2EE" strokeWidth="2" />
      <text x={cx0} y={cy0 - 18} textAnchor="middle" fill="#F5F2EE" fontSize="44" fontWeight="500">{pct(value)}</text>
      <text x={cx0} y={cy0 + 8} textAnchor="middle" fill="#A39B93" fontSize="13">Test accuracy</text>
    </svg>
  );
}

export default function DashboardPage() {
  const nav = useNavigate();
  const { data, error, loading, reload } = useApi(() => api.dashboard(), []);
  const metrics = useApi(() => api.metrics(), []);
  if (loading && !data) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return null;

  const m = data.model;
  const threshold = m.referral_threshold ?? 0.5;
  const daily = data.daily.map((d) => ({ ...d, day: new Date(d.date).toLocaleDateString("en-GB", { weekday: "short" }).slice(0, 2), total: d.normal + d.pneumonia }));
  const weekTotal = daily.reduce((s, d) => s + d.total, 0);
  const recentUnc = data.uncertainty_series.slice(-12);
  const series = data.uncertainty_series.map((p, i) => ({ i: i + 1, u: p.uncertainty }));
  const pneuShare = data.total ? data.pneumonia / data.total : 0;
  const acc = metrics.data?.available ? metrics.data.accuracy : null;

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_1fr_1fr_0.95fr]">
      {/* -------- row 1 -------- */}
      <section className="card p-5">
        <CardHead icon={<IconTile tone="orange"><ScanLine className="h-5 w-5" /></IconTile>} title="Analyses" note="Last 7 days" />
        <div className="mt-4 flex items-end justify-between gap-3">
          <div>
            <div className="num text-[38px] font-medium leading-none text-ink">{data.total}</div>
            <div className="mt-2 flex items-center gap-1.5 text-[12.5px] text-muted"><Activity className="h-3.5 w-3.5" />{weekTotal} this week</div>
          </div>
          <div className="h-[92px] w-[60%]">
            <ResponsiveContainer>
              <BarChart data={daily} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
                <XAxis dataKey="day" {...axisProps} axisLine={false} tick={{ ...axisProps.tick, fontSize: 10 }} />
                <Tooltip {...tooltipProps} formatter={(v: number) => [v, "X-rays"]} />
                <Bar dataKey="total" radius={[6, 6, 6, 6]} fill={C.brand} isAnimationActive={false} minPointSize={3} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="card p-5">
        <CardHead icon={<IconTile><Stethoscope className="h-5 w-5" /></IconTile>} title="Predictions" note="All time" />
        <div className="mt-4 flex items-end gap-6">
          <div><div className="num text-[38px] font-medium leading-none text-danger">{data.pneumonia}</div><div className="mt-2 text-[12.5px] text-muted">Pneumonia</div></div>
          <div><div className="num text-[38px] font-medium leading-none text-ok">{data.normal}</div><div className="mt-2 text-[12.5px] text-muted">Normal</div></div>
        </div>
        <div className="mt-5 flex h-2.5 overflow-hidden rounded-full bg-white/10">
          <div className="h-full bg-danger" style={{ width: `${pneuShare * 100}%` }} />
          <div className="h-full flex-1 bg-ok" style={{ opacity: data.total ? 1 : 0 }} />
        </div>
        <div className="mt-1.5 flex justify-between text-[11.5px] text-muted"><span>{pct(pneuShare, 0)} pneumonia</span><span>{pct(data.total ? 1 - pneuShare : 0, 0)} normal</span></div>
      </section>

      <section className="card p-5">
        <CardHead icon={<IconTile tone="rose"><HelpCircle className="h-5 w-5" /></IconTile>} title="Referred" note="Uncertain" />
        <div className="mt-4 flex items-end justify-between gap-3">
          <div>
            <div className="num text-[38px] font-medium leading-none text-ink">{data.referred}<span className="ml-1 text-[16px] text-muted">REFER</span></div>
            <div className="mt-2 text-[12.5px] text-muted">Avg uncertainty {pct(data.average_uncertainty)}</div>
          </div>
          {/* recent uncertainty bars, amber above threshold */}
          <div className="flex h-[88px] items-end gap-1.5">
            {recentUnc.length === 0 ? <span className="text-[12px] text-muted">No data</span> : recentUnc.map((p, i) => (
              <span key={i} title={`Uncertainty ${pct(p.uncertainty)}`} className="w-3.5 rounded-md"
                style={{ height: `${Math.max(8, p.uncertainty * 88)}px`, background: p.uncertainty > threshold ? C.amber : "rgba(255,255,255,0.22)" }} />
            ))}
          </div>
        </div>
      </section>

      {/* -------- tall right card: model gauge -------- */}
      <section className="card relative overflow-hidden p-5 lg:row-span-2">
        <div className="pointer-events-none absolute inset-0 bg-cover bg-center opacity-35" style={{ backgroundImage: "url(/images/login-bg.webp)" }} aria-hidden />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-black/30 via-black/10 to-black/70" aria-hidden />
        <div className="relative flex h-full flex-col">
          <div className="flex justify-center gap-2">
            {[ScanLine, Brain, Wind, Eye, LineIcon].map((I, i) => (
              <span key={i} className={cx("flex h-10 w-10 items-center justify-center rounded-full border border-white/20 backdrop-blur-md",
                i === 2 ? "h-12 w-12 bg-white/25" : "bg-white/10")}>
                <I className="h-4 w-4 text-white" />
              </span>
            ))}
          </div>
          <div className="mt-6 text-center text-[13px] text-white/80">Model accuracy</div>
          <div className="mt-2 px-2">{acc !== null ? <Gauge value={acc} /> : <div className="py-16 text-center text-[13px] text-muted">{metrics.loading ? "Loading…" : "No evaluation"}</div>}</div>
          <div className="mt-auto pt-6 text-center">
            <div className="flex items-center justify-center gap-2 text-[17px] font-medium text-white">
              <span className={cx("h-2.5 w-2.5 rounded-full", m.available ? "bg-ok" : "bg-warn")} />{m.available ? "Model ready" : "Model pending"}
            </div>
            <div className="mt-1 text-[12.5px] text-white/70">ResNet-50 · {m.version}{metrics.data?.available ? ` · ROC-AUC ${metrics.data.roc_auc.toFixed(3)}` : ""}</div>
            <Link to="/performance" className="btn-secondary btn-sm mt-4">View performance</Link>
          </div>
        </div>
      </section>

      {/* -------- row 2 -------- */}
      <section className="card p-5 lg:col-span-2">
        <div className="flex items-start justify-between">
          <span className="text-[15px] text-ink-soft">Uncertainty trend</span>
          <span className="text-[12px] text-muted">Last {series.length} analyses</span>
        </div>
        <div className="mt-1 text-center">
          <div className="num text-[30px] font-medium text-brand-600">{pct(data.average_uncertainty, 0)}</div>
          <div className="text-[13px] text-ink-soft">Average uncertainty</div>
        </div>
        <div className="mt-2 h-[120px]">
          {series.length < 2 ? <p className="pt-10 text-center text-[13px] text-muted">Analyse more X-rays to see a trend.</p> : (
            <ResponsiveContainer>
              <AreaChart data={series} margin={{ top: 6, right: 4, left: 4, bottom: 0 }}>
                <defs>
                  <linearGradient id="uncFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={C.brand} stopOpacity={0.45} />
                    <stop offset="100%" stopColor={C.brand} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <YAxis domain={[0, 1]} hide />
                <XAxis dataKey="i" hide />
                <Tooltip {...tooltipProps} formatter={(v: number) => [pct(v), "Uncertainty"]} labelFormatter={(l) => `Analysis #${l}`} />
                <ReferenceLine y={threshold} stroke={C.amber} strokeDasharray="4 4" />
                <Area type="monotone" dataKey="u" stroke={C.brand} strokeWidth={2.5} fill="url(#uncFill)" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
        <div className="mt-3 grid grid-cols-3 text-[12.5px]">
          <div><div className="text-muted">Referral threshold</div><div className="mt-0.5 text-[15px] font-medium text-ink">{pct(threshold)}</div></div>
          <div className="text-center"><div className="text-muted">AUTO</div><div className="mt-0.5 text-[15px] font-medium text-ink">{data.auto}</div></div>
          <div className="text-right"><div className="text-muted">REFER</div><div className="mt-0.5 text-[15px] font-medium text-ink">{data.referred}</div></div>
        </div>
      </section>

      <section className="card p-5">
        <div className="flex items-center justify-between">
          <span className="text-[15px] text-ink-soft">Recent analyses</span>
          {data.total > 0 && <Link to="/history" className="text-[12.5px] text-brand-600 hover:underline">View all</Link>}
        </div>
        {data.recent.length === 0 ? (
          <div className="py-8 text-center">
            <p className="text-[13.5px] text-muted">No analyses yet.</p>
            <Link to="/analyse" className="btn-primary btn-sm mt-3">Analyse X-ray</Link>
          </div>
        ) : (
          <ul className="mt-3 space-y-2">
            {data.recent.map((a) => (
              <li key={a.id}>
                <button onClick={() => nav(`/history/${a.id}`)} className="flex w-full items-center gap-3 rounded-2xl bg-white/[0.04] px-3 py-2.5 text-left hover:bg-white/[0.08]">
                  <PredictionBadge value={a.prediction} />
                  <DecisionBadge value={a.decision} />
                  <span className="ml-auto text-[11.5px] text-muted">{dateTime(a.created_at)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
