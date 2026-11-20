import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { api, assetUrl, errorMessage } from "../services/api";
import type { Analysis } from "../types";
import { dateTime, pct } from "../utils/format";
import { Bar, Card, cx, DecisionBadge, PredictionBadge } from "./ui";

/** Low / Moderate / High, relative to the referral threshold. */
export function uncertaintyLevel(u: number, threshold: number) {
  if (u > threshold) return { label: "High", tone: "text-warn" };
  if (u > threshold / 2) return { label: "Moderate", tone: "text-brand-600" };
  return { label: "Low", tone: "text-ok" };
}

/** Uncertainty score on a 0–100% scale with the referral threshold marked. */
function UncertaintyCard({ a }: { a: Analysis }) {
  const refer = a.decision === "REFER";
  const level = uncertaintyLevel(a.uncertainty, a.referral_threshold);
  const pos = (v: number) => `${Math.max(0, Math.min(1, v)) * 100}%`;
  return (
    <Card title="Uncertainty">
      <div className="flex items-end justify-between gap-4">
        <div>
          <div className="num text-[30px] font-semibold leading-none">{pct(a.uncertainty)}</div>
          <div className={cx("mt-1.5 text-[14px] font-semibold", level.tone)}>{level.label} uncertainty</div>
        </div>
        <DecisionBadge value={a.decision} />
      </div>

      <div className="relative mt-7 mb-7">
        {/* scale: AUTO zone (left of threshold) and REFER zone (right) */}
        <div className="flex h-3 overflow-hidden rounded-full">
          <div className="h-full bg-brand-100" style={{ width: pos(a.referral_threshold) }} />
          <div className="h-full flex-1 bg-warn-bg" style={{ boxShadow: "inset 0 0 0 1px #EBD9B2" }} />
        </div>
        <div className="absolute -top-1 bottom-[-4px] w-0.5 bg-black/60" style={{ left: pos(a.referral_threshold) }} />
        <div className="absolute -top-6 -translate-x-1/2 whitespace-nowrap text-[11.5px] text-muted" style={{ left: pos(a.referral_threshold) }}>
          threshold {pct(a.referral_threshold, 0)}
        </div>
        <div className={cx("absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-white shadow",
          refer ? "bg-warn" : "bg-brand-700")} style={{ left: pos(a.uncertainty) }} />
        <div className="mt-2 flex justify-between text-[11.5px] text-muted">
          <span>0% · certain</span><span className="font-medium text-brand-700">AUTO</span>
          <span className="font-medium text-warn">REFER</span><span>100% · uncertain</span>
        </div>
      </div>

      <div className={cx("rounded-md border px-4 py-3 text-[13.5px]", refer ? "border-warn-line bg-warn-bg" : "border-brand-200 bg-brand-50")}>
        <b className="text-ink">{refer ? "REFER — needs specialist review." : "AUTO — confident result."}</b>{" "}
        <span className="text-ink-soft">{a.decision_reason}</span>
      </div>
    </Card>
  );
}

/** Shows one analysis: prediction, probability, uncertainty, decision and Grad-CAM. */
export default function ResultView({ initial }: { initial: Analysis }) {
  const [a, setA] = useState(initial);
  const [view, setView] = useState<"heatmap" | "original">("heatmap");
  const [camState, setCamState] = useState<"idle" | "loading" | "error">("idle");
  const [camError, setCamError] = useState("");

  useEffect(() => setA(initial), [initial]);

  // Generate the heatmap automatically the first time a result is shown.
  useEffect(() => {
    if (a.gradcam_url) return;
    let alive = true;
    setCamState("loading");
    api.gradcam(a.id)
      .then((r) => { if (alive) { setA(r); setCamState("idle"); } })
      .catch((e) => { if (alive) { setCamState("error"); setCamError(errorMessage(e, "Heatmap unavailable.")); } });
    return () => { alive = false; };
  }, [a.id, a.gradcam_url]);

  const showHeatmap = view === "heatmap" && a.gradcam_url;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <Card title="Image" actions={
        <div className="inline-flex rounded-md border border-line-strong p-0.5 text-[12.5px]">
          {(["heatmap", "original"] as const).map((v) => (
            <button key={v} onClick={() => setView(v)}
              className={cx("rounded px-3 py-1 font-medium capitalize", view === v ? "bg-brand-700 text-white" : "text-ink-soft hover:bg-subtle")}>
              {v === "heatmap" ? "Grad-CAM" : "Original"}
            </button>
          ))}
        </div>
      }>
        <div className="relative flex aspect-square items-center justify-center overflow-hidden rounded-md bg-black">
          <img src={assetUrl(showHeatmap ? a.gradcam_url! : a.image_url)} alt={showHeatmap ? "Grad-CAM heatmap" : "Chest X-ray"}
            className="h-full w-full object-contain" />
          {view === "heatmap" && !a.gradcam_url && (
            <div className="absolute inset-0 flex items-center justify-center bg-black/60 text-[13px] text-white">
              {camState === "loading" ? <span className="flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" />Generating heatmap…</span>
                : camState === "error" ? camError : null}
            </div>
          )}
        </div>
        {showHeatmap && <p className="mt-3 text-[12.5px] text-muted">Red areas had the most influence on the prediction.</p>}
      </Card>

      <div className="space-y-6">
        <Card>
          <div className="text-[13px] text-muted">Prediction</div>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <PredictionBadge value={a.prediction} size="lg" />
            <DecisionBadge value={a.decision} />
          </div>

          <div className="mt-6">
            <div className="mb-1.5 flex justify-between text-[14px]"><span className="text-ink-soft">Pneumonia probability</span><span className="num font-semibold">{pct(a.pneumonia_probability)}</span></div>
            <Bar value={a.pneumonia_probability} tone={a.pneumonia_probability >= 0.5 ? "danger" : "ok"} />
          </div>
        </Card>

        <UncertaintyCard a={a} />

        <Card>
          <dl className="grid grid-cols-2 gap-4 text-[13.5px]">
            <div><dt className="text-muted">Date</dt><dd className="mt-0.5 font-medium">{dateTime(a.created_at)}</dd></div>
            <div><dt className="text-muted">Model</dt><dd className="mt-0.5 font-medium">ResNet-50 · {a.model_version}</dd></div>
            <div><dt className="text-muted">Image size</dt><dd className="mt-0.5 font-medium">{a.image_width} × {a.image_height}</dd></div>
            <div><dt className="text-muted">Processing time</dt><dd className="mt-0.5 font-medium">{(a.processing_ms / 1000).toFixed(2)} s</dd></div>
          </dl>
        </Card>
      </div>
    </div>
  );
}
