import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { axisProps, C, gridProps, legendProps, tooltipProps } from "../components/charts/theme";
import type { Metrics } from "../types";

function UncertaintySection({ u }: { u: Metrics["uncertainty"] }) {
  const stats = [
    ["Referred (REFER)", pct(u.refer_rate), `${u.n_referred} test X-rays`],
    ["Accuracy on AUTO cases", pct(u.auto_accuracy), `vs ${pct(u.overall_accuracy)} on all cases`],
    ["Mistakes caught by REFER", `${u.errors_caught} / ${u.total_errors}`, "wrong predictions sent for review"],
    ["Average uncertainty", pct(u.mean_uncertainty), `referral threshold ${pct(u.referral_threshold)}`],
  ];
  return (
    <Card title="Uncertainty & referral">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {stats.map(([label, value, hint]) => (
          <div key={label} className="rounded-md border border-line bg-subtle px-4 py-3">
            <div className="text-[12.5px] text-muted">{label}</div>
            <div className="num mt-1 text-[22px] font-semibold">{value}</div>
            <div className="mt-0.5 text-[12px] text-muted">{hint}</div>
          </div>
        ))}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div>
          <div className="mb-2 text-[13.5px] font-medium">Uncertainty of correct vs wrong predictions</div>
          <div style={{ height: 230 }}>
            <ResponsiveContainer>
              <BarChart data={u.histogram} margin={{ left: -14, right: 8, top: 6 }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="bin" {...axisProps} tickFormatter={(v) => `${Math.round(v * 100)}%`} interval={3} />
                <YAxis {...axisProps} scale="sqrt" allowDecimals={false} />
                <Tooltip {...tooltipProps} labelFormatter={(l) => `Uncertainty ≈ ${Math.round(+l * 100)}%`} />
                <Legend {...legendProps} iconType="square" />
                <ReferenceLine x={u.histogram.reduce((b, h) => Math.abs(h.bin - u.referral_threshold) < Math.abs(b.bin - u.referral_threshold) ? h : b).bin}
                  stroke={C.warn} strokeDasharray="4 3" />
                <Bar dataKey="correct" name="Correct" stackId="a" fill={C.brand} isAnimationActive={false} />
                <Bar dataKey="wrong" name="Wrong" stackId="a" fill={C.danger} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-1 text-[12px] text-muted">Wrong predictions mostly have high uncertainty. Dashed line = referral threshold.</p>
        </div>
        <div>
          <div className="mb-2 text-[13.5px] font-medium">Accuracy as more uncertain cases are referred</div>
          <div style={{ height: 230 }}>
            <ResponsiveContainer>
              <LineChart data={u.accuracy_vs_referred} margin={{ left: -6, right: 8, top: 6 }}>
                <CartesianGrid {...gridProps} />
                <XAxis dataKey="referred" type="number" domain={[0, 0.95]} {...axisProps} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
                <YAxis domain={[0.9, 1]} {...axisProps} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
                <Tooltip {...tooltipProps} formatter={(v: number) => [pct(v), "Accuracy"]} labelFormatter={(l) => `${Math.round(+l * 100)}% referred`} />
                <ReferenceLine x={u.refer_rate} stroke={C.warn} strokeDasharray="4 3" />
                <Line dataKey="accuracy" stroke={C.brand} strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-1 text-[12px] text-muted">Referring the most uncertain X-rays raises accuracy on the rest. Dashed line = current setting.</p>
        </div>
      </div>
    </Card>
  );
}
import { Card, cx, Empty, ErrorBox, Loading, PageHeader } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import { num, pct } from "../utils/format";

export default function PerformancePage() {
  const { data: m, error, loading, reload } = useApi(() => api.metrics(), []);

  if (loading && !m) return <Loading />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!m) return null;
  if (!m.available) {
    return (
      <div className="space-y-6">
        <PageHeader title="Model Performance" />
        <Card><Empty title="No evaluation results" text={m.message} /></Card>
      </div>
    );
  }

  const tiles = [
    ["Accuracy", m.accuracy], ["Precision", m.precision], ["Recall", m.recall], ["F1-score", m.f1], ["ROC-AUC", m.roc_auc],
  ] as const;
  const cm = m.confusion_matrix;
  const roc = [...m.roc_curve];

  return (
    <div className="space-y-6">
      <PageHeader title="Model Performance" subtitle={`${m.dataset} · ${m.n_images} images (${m.n_pneumonia} pneumonia, ${m.n_normal} normal)`} />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
        {tiles.map(([label, v]) => (
          <div key={label} className="card px-5 py-5">
            <div className="text-[13px] text-muted">{label}</div>
            <div className="num mt-2 text-[26px] font-semibold leading-none">{label === "ROC-AUC" ? num(v) : pct(v)}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Confusion matrix">
          <div className="grid grid-cols-[auto_1fr_1fr] gap-2 text-[13px]">
            <div />
            <div className="pb-1 text-center text-muted">Predicted normal</div>
            <div className="pb-1 text-center text-muted">Predicted pneumonia</div>
            {([
              ["Actual normal", cm.tn, "Correct", true, cm.fp, "False positive", false],
              ["Actual pneumonia", cm.fn, "False negative", false, cm.tp, "Correct", true],
            ] as const).map(([row, a, al, aok, b, bl, bok]) => (
              <div key={row} className="contents">
                <div className="flex items-center pr-3 text-muted">{row}</div>
                {[[a, al, aok], [b, bl, bok]].map(([v, l, ok], i) => (
                  <div key={i} className={cx("rounded-md border px-3 py-5 text-center", ok ? "border-ok-line bg-ok-bg" : "border-danger-line bg-danger-bg")}>
                    <div className="num text-[24px] font-semibold">{v as number}</div>
                    <div className="text-[12px] text-muted">{l as string}</div>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </Card>

        <Card title={`ROC curve (AUC ${num(m.roc_auc)})`}>
          <div style={{ height: 260 }}>
            <ResponsiveContainer>
              <ComposedChart data={roc} margin={{ left: -10, right: 10, top: 6, bottom: 6 }}>
                <CartesianGrid {...gridProps} vertical />
                <XAxis type="number" dataKey="x" domain={[0, 1]} {...axisProps}
                  label={{ value: "False positive rate", position: "insideBottom", offset: -4, fontSize: 11, fill: "#747B78" }} />
                <YAxis type="number" domain={[0, 1]} {...axisProps}
                  label={{ value: "True positive rate", angle: -90, position: "insideLeft", offset: 18, fontSize: 11, fill: "#747B78" }} />
                <Tooltip {...tooltipProps} formatter={(v: number) => v.toFixed(3)} labelFormatter={(l) => `FPR ${(+l).toFixed(3)}`} />
                <Area dataKey="y" name="TPR" stroke={C.brand} fill={C.brand} fillOpacity={0.08} strokeWidth={2} isAnimationActive={false} />
                <Line data={[{ x: 0, y: 0 }, { x: 1, y: 1 }]} dataKey="y" stroke={C.ref} strokeDasharray="4 3" dot={false} isAnimationActive={false} legendType="none" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {m.uncertainty && <UncertaintySection u={m.uncertainty} />}

      <Card title="Summary">
        <ul className="space-y-2 text-[14px] text-ink-soft">
          <li>• The model correctly classified <b className="text-ink">{pct(m.accuracy)}</b> of test X-rays and detected <b className="text-ink">{pct(m.recall)}</b> of pneumonia cases.</li>
          <li>• ROC-AUC of <b className="text-ink">{num(m.roc_auc)}</b>{m.roc_auc_ci && <> (95% CI {num(m.roc_auc_ci.lower)}–{num(m.roc_auc_ci.upper)})</>}.</li>
          <li>• <b className="text-ink">{pct(m.refer_rate)}</b> of test X-rays were referred for review; accuracy on the rest was <b className="text-ink">{pct(m.auto_accuracy)}</b>.</li>
          <li>• External test on the RSNA dataset: {m.external_rsna ? <>accuracy {pct(m.external_rsna.accuracy)}, ROC-AUC {num(m.external_rsna.roc_auc)}.</> : "not yet run."}</li>
        </ul>
      </Card>
    </div>
  );
}

