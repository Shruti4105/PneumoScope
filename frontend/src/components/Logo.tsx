import { Link } from "react-router-dom";
import { cx } from "./ui";

export function Logo({ inverted = false, to = "/" }: { inverted?: boolean; to?: string }) {
  return (
    <Link to={to} className="flex items-center gap-2.5" aria-label="PneumoScope">
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
        <rect width="32" height="32" rx={inverted ? 16 : 8} fill={inverted ? "#F06C38" : "#24483F"} />
        <path d="M16 7v18M11.5 11c-3 1-4.5 4.5-4.5 8.5 0 2.5 1.3 3.5 3 3.5s3-1.4 3-4v-6.5M20.5 11c3 1 4.5 4.5 4.5 8.5 0 2.5-1.3 3.5-3 3.5s-3-1.4-3-4v-6.5"
          fill="none" stroke="#FFFFFF" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className={cx("text-[16px] font-semibold tracking-tight", inverted ? "text-white" : "text-ink")}>PneumoScope</span>
    </Link>
  );
}
