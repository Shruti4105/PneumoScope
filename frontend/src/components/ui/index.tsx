import { AlertCircle, Inbox, Loader2, RefreshCw, X } from "lucide-react";
import { useEffect, type ReactNode } from "react";
import type { Decision, Prediction } from "../../types";

export function cx(...c: (string | false | null | undefined)[]) {
  return c.filter(Boolean).join(" ");
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-[24px] font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 text-[14px] text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ title, actions, children, className, bodyClass }: {
  title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string; bodyClass?: string;
}) {
  return (
    <section className={cx("card", className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
          {title && <h2 className="text-[15px] font-semibold">{title}</h2>}
          {actions}
        </header>
      )}
      <div className={cx("p-5", bodyClass)}>{children}</div>
    </section>
  );
}

export function Stat({ label, value, icon, hint }: { label: string; value: ReactNode; icon?: ReactNode; hint?: string }) {
  return (
    <div className="card px-5 py-5">
      <div className="flex items-center justify-between text-[13px] text-muted">{label}{icon}</div>
      <div className="num mt-2 text-[28px] font-semibold leading-none text-ink">{value}</div>
      {hint && <div className="mt-2 text-[12.5px] text-muted">{hint}</div>}
    </div>
  );
}

export function PredictionBadge({ value, size = "sm" }: { value: Prediction; size?: "sm" | "lg" }) {
  const pos = value === "PNEUMONIA";
  return (
    <span className={cx("inline-flex items-center gap-1.5 rounded-md border font-semibold",
      size === "lg" ? "px-3 py-1.5 text-[15px]" : "px-2 py-0.5 text-[12px]",
      pos ? "border-danger-line bg-danger-bg text-danger" : "border-ok-line bg-ok-bg text-ok")}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />{pos ? "Pneumonia" : "Normal"}
    </span>
  );
}

export function DecisionBadge({ value }: { value: Decision }) {
  return (
    <span className={cx("inline-flex rounded-md border px-2 py-0.5 text-[12px] font-semibold tracking-wide",
      value === "REFER" ? "border-warn-line bg-warn-bg text-warn" : "border-brand-200 bg-brand-50 text-brand-700")}>
      {value}
    </span>
  );
}

export function Bar({ value, tone = "brand" }: { value: number; tone?: "brand" | "danger" | "ok" | "warn" }) {
  const c = { brand: "bg-brand-700", danger: "bg-danger", ok: "bg-ok", warn: "bg-warn" }[tone];
  return (
    <div className="h-2 overflow-hidden rounded-full bg-line">
      <div className={cx("h-full rounded-full", c)} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
    </div>
  );
}

export function Loading({ label = "Loading…", className }: { label?: string; className?: string }) {
  return (
    <div className={cx("flex items-center justify-center gap-2 py-16 text-[13.5px] text-muted", className)}>
      <Loader2 className="h-4 w-4 animate-spin text-brand-600" /> {label}
    </div>
  );
}

export function Empty({ title, text, action }: { title: string; text?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center px-6 py-12 text-center">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-subtle text-muted"><Inbox className="h-5 w-5" /></div>
      <div className="text-[15px] font-semibold">{title}</div>
      {text && <p className="mt-1 max-w-sm text-[13.5px] text-muted">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-danger-line bg-danger-bg px-4 py-3 text-[13.5px] text-ink-soft">
      <AlertCircle className="h-5 w-5 shrink-0 text-danger" />
      <span className="flex-1">{message}</span>
      {onRetry && <button className="btn-secondary btn-sm" onClick={onRetry}><RefreshCw className="h-3.5 w-3.5" />Retry</button>}
    </div>
  );
}

export function Modal({ open, onClose, title, children, footer }: {
  open: boolean; onClose: () => void; title: string; children: ReactNode; footer?: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onMouseDown={onClose} role="dialog" aria-modal="true" aria-label={title}>
      <div className="card w-full max-w-md shadow-raised" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 className="text-[15px] font-semibold">{title}</h2>
          <button className="rounded p-1 text-muted hover:bg-subtle" onClick={onClose} aria-label="Close"><X className="h-4 w-4" /></button>
        </div>
        <div className="px-5 py-4 text-[14px] text-ink-soft">{children}</div>
        {footer && <div className="flex justify-end gap-2 border-t border-line px-5 py-3">{footer}</div>}
      </div>
    </div>
  );
}
