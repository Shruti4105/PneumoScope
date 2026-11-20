import { BarChart3, History, Home, Info, LogOut, Plus, ScanLine } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { cx } from "../components/ui";
import { useAuth } from "../context/AuthContext";

const NAV = [
  { to: "/dashboard", label: "Dashboard", icon: Home },
  { to: "/analyse", label: "X-Ray Analysis", icon: ScanLine },
  { to: "/history", label: "Analysis History", icon: History },
  { to: "/performance", label: "Model Performance", icon: BarChart3 },
  { to: "/about", label: "About Project", icon: Info },
];

const SUBTITLES: Record<string, string> = {
  "/dashboard": "Here's your overview",
  "/analyse": "Upload a chest X-ray",
  "/history": "Your past analyses",
  "/performance": "How the model performs",
  "/about": "About the project",
};

function LogoBadge() {
  return (
    <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-700 shadow-[0_8px_24px_-8px_rgba(240,108,56,0.9)]">
      <svg viewBox="0 0 32 32" className="h-7 w-7" aria-hidden="true">
        <path d="M16 7v18M11.5 11c-3 1-4.5 4.5-4.5 8.5 0 2.5 1.3 3.5 3 3.5s3-1.4 3-4v-6.5M20.5 11c3 1 4.5 4.5 4.5 8.5 0 2.5-1.3 3.5-3 3.5s-3-1.4-3-4v-6.5"
          fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

function RailLink({ to, label, icon: Icon }: { to: string; label: string; icon: typeof Home }) {
  return (
    <NavLink to={to} title={label} aria-label={label}
      className={({ isActive }) => cx(
        "group relative flex h-12 w-12 shrink-0 items-center justify-center rounded-full border transition-colors",
        isActive ? "border-white bg-white text-[#14110F]" : "border-white/15 bg-white/[0.04] text-ink-soft hover:border-white/40 hover:text-ink")}>
      <Icon className="h-[19px] w-[19px]" strokeWidth={1.8} />
      <span className="pointer-events-none absolute left-14 z-50 hidden whitespace-nowrap rounded-full bg-black/85 px-3 py-1 text-[12.5px] text-white lg:group-hover:block">
        {label}
      </span>
    </NavLink>
  );
}

function UserMenu() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  if (!user) return null;
  const initials = user.name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)} className="flex items-center gap-3 rounded-full py-1 pl-1 pr-3 hover:bg-white/5" aria-haspopup="menu" aria-expanded={open} aria-label="Account menu">
        <span className="flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-gradient-to-br from-brand-500 to-brand-900 text-[14px] font-semibold text-white">{initials}</span>
        <span className="hidden text-left leading-tight md:block">
          <span className="block text-[14px] font-semibold text-ink">{user.name}</span>
          <span className="block max-w-[160px] truncate text-[12px] text-muted">{user.email}</span>
        </span>
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-40 mt-2 w-48 overflow-hidden rounded-2xl border border-white/10 bg-[#1E1B19]/95 py-1 shadow-xl backdrop-blur-xl" role="menu">
            <button className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-[13.5px] text-danger hover:bg-white/5" aria-label="Sign out"
              onClick={async () => { await logout(); nav("/login"); }}>
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default function AppLayout() {
  const { user } = useAuth();
  const loc = useLocation();
  const base = "/" + (loc.pathname.split("/")[1] ?? "");
  const first = user?.name.split(" ")[0] ?? "";
  useEffect(() => { window.scrollTo(0, 0); }, [loc.pathname]);

  return (
    <div className="theme-dark relative min-h-screen bg-[#0B0908] text-ink">
      {/* cinematic background */}
      <div className="pointer-events-none fixed inset-0 bg-cover bg-top" style={{ backgroundImage: "url(/images/app-bg.webp)" }} aria-hidden />
      <div className="pointer-events-none fixed inset-0 bg-gradient-to-b from-black/10 via-black/30 to-black/80" aria-hidden />

      {/* left icon rail (desktop) */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-24 flex-col items-center gap-3 py-7 lg:flex">
        <Link to="/dashboard" aria-label="PneumoScope dashboard" className="mb-6"><LogoBadge /></Link>
        {NAV.map((n) => <RailLink key={n.to} {...n} />)}
      </aside>

      <div className="relative lg:pl-24">
        {/* top bar */}
        <header className="relative z-20 grid grid-cols-[1fr_auto] items-start gap-4 px-4 pt-5 sm:px-8 lg:grid-cols-[1fr_auto_1fr] lg:pt-8">
          <div className="flex items-center gap-3">
            <Link to="/dashboard" className="lg:hidden" aria-label="PneumoScope dashboard"><LogoBadge /></Link>
            <div className="leading-tight">
              <span className="block text-[15px] font-semibold text-ink">PneumoScope</span>
              <span className="block text-[12px] text-muted">Dashboard</span>
            </div>
          </div>
          <div className="order-3 col-span-2 text-center lg:order-none lg:col-span-1">
            <div className="text-[19px] font-semibold text-ink sm:text-[22px]">Hey, {first}</div>
            <div className="mt-1 text-[26px] font-light text-ink/80 sm:text-[34px]">{SUBTITLES[base] ?? ""}</div>
          </div>
          <div className="flex items-center justify-end gap-3">
            <Link to="/analyse" title="New analysis" aria-label="New analysis"
              className="flex h-12 w-12 items-center justify-center rounded-full border border-white/20 bg-white/[0.04] text-ink hover:bg-white/10">
              <Plus className="h-5 w-5" />
            </Link>
            <UserMenu />
          </div>
        </header>

        {/* icon nav for tablets and phones */}
        <nav className="sticky top-0 z-20 mt-4 flex justify-center gap-2 px-4 py-2 backdrop-blur-md lg:hidden" aria-label="Main navigation">
          {NAV.map((n) => <RailLink key={n.to} {...n} />)}
        </nav>

        <main className="relative z-10 mx-auto max-w-[1280px] px-4 pb-10 pt-6 sm:px-8 lg:pt-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
