import { CheckCircle2, FileImage, Loader2, RefreshCw, ScanLine, Trash2, UploadCloud } from "lucide-react";
import { useEffect, useRef, useState, type DragEvent } from "react";
import { Link } from "react-router-dom";
import ResultView from "../components/ResultView";
import { Card, cx, ErrorBox, PageHeader } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { api, errorMessage } from "../services/api";
import type { Analysis } from "../types";

const MAX_MB = 10;
const EXT = /\.(jpe?g|png)$/i;

function imageSize(url: string): Promise<{ w: number; h: number }> {
  return new Promise((res, rej) => {
    const img = new Image();
    img.onload = () => res({ w: img.naturalWidth, h: img.naturalHeight });
    img.onerror = rej;
    img.src = url;
  });
}

export default function AnalysePage() {
  const model = useApi(() => api.modelInfo(), []);
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<Analysis | null>(null);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  async function choose(f: File) {
    setError(null);
    setResult(null);
    if (!EXT.test(f.name) || !["image/jpeg", "image/png", ""].includes(f.type)) return setError("Please choose a JPG or PNG image.");
    if (f.size > MAX_MB * 1024 * 1024) return setError(`The file is larger than ${MAX_MB} MB.`);
    const url = URL.createObjectURL(f);
    try {
      const { w, h } = await imageSize(url);
      if (Math.min(w, h) < 128) { URL.revokeObjectURL(url); return setError("The image is too small (minimum 128 px)."); }
    } catch {
      URL.revokeObjectURL(url);
      return setError("This file could not be read as an image.");
    }
    setPreview((old) => { if (old) URL.revokeObjectURL(old); return url; });
    setFile(f);
  }

  function reset() {
    setFile(null);
    setPreview((old) => { if (old) URL.revokeObjectURL(old); return null; });
    setResult(null);
    setError(null);
    if (input.current) input.current.value = "";
  }

  async function analyse() {
    if (!file) return;
    setBusy(true);
    setError(null);
    setProgress(0);
    try {
      setResult(await api.triage(file, setProgress));
    } catch (e) {
      setError(errorMessage(e, "Analysis failed."));
    } finally {
      setBusy(false);
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files?.[0];
    if (f) void choose(f);
  }

  const unavailable = model.data && !model.data.available;

  if (result) {
    return (
      <div className="space-y-6">
        <PageHeader title="Analysis result"
          actions={<>
            <button className="btn-primary" onClick={reset}><ScanLine className="h-4 w-4" />Analyse another</button>
            <Link to="/history" className="btn-secondary">View history</Link>
          </>} />
        <div className="flex items-center gap-2 text-[13.5px] text-ok"><CheckCircle2 className="h-4 w-4" />Saved to analysis history.</div>
        <ResultView initial={result} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader title="X-Ray Analysis" subtitle="Upload a chest X-ray (JPG or PNG, up to 10 MB)." />
      {unavailable && <ErrorBox message={model.data!.message} />}

      <Card className="mx-auto max-w-2xl">
        {!file ? (
          <div onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)} onDrop={onDrop}
            className={cx("flex flex-col items-center rounded-lg border-2 border-dashed px-6 py-16 text-center transition-colors",
              drag ? "border-brand-500 bg-brand-50" : "border-line-strong bg-subtle")}>
            <UploadCloud className="h-10 w-10 text-brand-600" strokeWidth={1.5} />
            <div className="mt-4 text-[15px] font-medium">Drag and drop an X-ray here</div>
            <div className="mt-1 text-[13px] text-muted">or</div>
            <button className="btn-primary mt-3" onClick={() => input.current?.click()}>Browse files</button>
          </div>
        ) : (
          <div>
            <div className="flex items-center justify-center overflow-hidden rounded-lg bg-black">
              <img src={preview!} alt="Selected X-ray" className="max-h-[420px] w-auto object-contain" />
            </div>
            <div className="mt-4 flex items-center gap-3 rounded-md border border-line px-3 py-2.5">
              <FileImage className="h-4 w-4 text-muted" />
              <span className="flex-1 truncate text-[13.5px]">{file.name} · {(file.size / 1024).toFixed(0)} KB</span>
              <button className="rounded p-1.5 text-muted hover:bg-subtle" title="Replace" onClick={() => input.current?.click()} disabled={busy}><RefreshCw className="h-4 w-4" /></button>
              <button className="rounded p-1.5 text-muted hover:bg-danger-bg hover:text-danger" title="Remove" onClick={reset} disabled={busy}><Trash2 className="h-4 w-4" /></button>
            </div>
          </div>
        )}
        <input ref={input} type="file" accept=".jpg,.jpeg,.png,image/jpeg,image/png" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) void choose(f); }} />

        {error && <div className="mt-4"><ErrorBox message={error} /></div>}

        {file && (
          <>
            {busy && (
              <div className="mt-4">
                <div className="mb-1 text-[12.5px] text-muted">{progress < 100 ? `Uploading… ${progress}%` : "Analysing…"}</div>
                <div className="h-1.5 overflow-hidden rounded-full bg-line"><div className="h-full bg-brand-600 transition-[width]" style={{ width: `${progress}%` }} /></div>
              </div>
            )}
            <button className="btn-primary mt-4 w-full py-3 text-[15px]" onClick={analyse} disabled={busy || !!unavailable}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanLine className="h-4 w-4" />}
              {busy ? "Analysing…" : "Analyse"}
            </button>
          </>
        )}
      </Card>
    </div>
  );
}
