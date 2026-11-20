export const pct = (v: number | null | undefined, digits = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : `${(v * 100).toFixed(digits)}%`;

export const num = (v: number | null | undefined, digits = 3) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : v.toFixed(digits);

const asUtc = (v: string) => new Date(v.endsWith("Z") || v.includes("+") ? v : `${v}Z`);

export function dateTime(v: string | null | undefined) {
  if (!v) return "—";
  return asUtc(v).toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function dateOnly(v: string | null | undefined) {
  if (!v) return "—";
  return asUtc(v).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}
