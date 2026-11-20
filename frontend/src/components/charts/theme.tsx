/** Chart styling for the dark app theme (orange / amber accents on dark glass). */
export const C = {
  brand: "#F06C38",
  brandSoft: "#F9A26C",
  amber: "#FBBF24",
  sage: "#A39B93",
  sageLight: "#5C5650",
  warn: "#FBBF24",
  danger: "#F87171",
  ok: "#6EE7B7",
  grid: "rgba(255,255,255,0.07)",
  axis: "#7C756E",
  ink: "#F5F2EE",
  ref: "rgba(255,255,255,0.35)",
};

export const axisProps = {
  stroke: C.axis,
  tick: { fill: "#A39B93", fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: "rgba(255,255,255,0.12)" },
} as const;

export const gridProps = { stroke: C.grid, strokeDasharray: "0", vertical: false } as const;

export const tooltipProps = {
  contentStyle: {
    background: "rgba(24,21,19,0.95)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 14, fontSize: 12,
    boxShadow: "0 8px 24px rgba(0,0,0,0.5)", padding: "8px 12px", color: "#F5F2EE",
  },
  labelStyle: { color: "#F5F2EE", fontWeight: 600, marginBottom: 2 },
  itemStyle: { color: "#D6D0C9", padding: 0 },
  cursor: { fill: "rgba(255,255,255,0.05)", stroke: "rgba(255,255,255,0.2)" },
} as const;

export const legendProps = { iconType: "plainline" as const, iconSize: 14, wrapperStyle: { fontSize: 12, color: "#D6D0C9" } };

export function ChartFrame({ height = 260, children }: { height?: number; children: React.ReactNode }) {
  return <div style={{ width: "100%", height }}>{children}</div>;
}

export const fmt3 = (v: number) => (typeof v === "number" ? v.toFixed(3) : v);
export const fmtPct = (v: number) => (typeof v === "number" ? `${(v * 100).toFixed(0)}%` : v);
