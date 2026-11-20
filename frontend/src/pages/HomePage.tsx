import { Activity, ArrowRight, Eye, HelpCircle, ScanLine, UploadCloud } from "lucide-react";
import { Link } from "react-router-dom";
import { Logo } from "../components/Logo";
import { useAuth } from "../context/AuthContext";

const ACCENT = "#F06C38";

function Pill({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-full border border-white/15 bg-white/[0.06] px-5 py-2.5 text-[14px] text-white backdrop-blur-md ${className}`}>{children}</div>;
}

export default function HomePage() {
  const { user } = useAuth();
  const start = user ? "/analyse" : "/login";

  return (
    <div className="relative min-h-screen bg-[#0B0908]">
      {/* same cinematic background as the dashboard */}
      <div className="pointer-events-none fixed inset-0 bg-cover bg-top" style={{ backgroundImage: "url(/images/app-bg.webp)" }} aria-hidden />
      <div className="pointer-events-none fixed inset-0 bg-gradient-to-b from-black/20 via-black/40 to-black/85" aria-hidden />
      <div className="relative">
      {/* ===================== HERO FRAME ===================== */}
      <section className="relative">
        <div className="relative flex min-h-screen flex-col overflow-hidden border-b border-white/10 bg-gradient-to-br from-[#221C18]/75 via-[#15120F]/60 to-[#0D0B0A]/80 text-white">
          {/* diagonal light streak + faint grid */}
          <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(115deg,transparent_20%,rgba(240,108,56,0.10)_38%,transparent_55%)]" aria-hidden />
          <div className="pointer-events-none absolute inset-0 opacity-[0.07]" aria-hidden
            style={{ backgroundImage: "linear-gradient(to right,#fff 1px,transparent 1px),linear-gradient(to bottom,#fff 1px,transparent 1px)", backgroundSize: "150px 150px" }} />

          {/* nav */}
          <header className="relative z-20 mx-auto flex w-full max-w-[1440px] items-center justify-between gap-4 px-6 pt-6 sm:px-12 sm:pt-9">
            <Logo inverted />
            <nav className="hidden items-center gap-7 text-[15px] text-white/85 md:flex" aria-label="Sections">
              <a href="#top" className="border-b-2 pb-0.5" style={{ color: ACCENT, borderColor: ACCENT }}>Home</a>
              <a href="#how" className="hover:text-white">How it works</a>
              <a href="#results" className="hover:text-white">Results</a>
              {user ? <Link to="/dashboard" className="hover:text-white">Dashboard</Link> : <Link to="/login" className="hover:text-white">Sign in</Link>}
            </nav>
            <Link to={user ? "/dashboard" : "/login?mode=register"}
              className="rounded-full border border-white/25 bg-white/15 px-6 py-3 text-[15px] font-medium text-white backdrop-blur-md transition hover:bg-white/25">
              {user ? "Open dashboard" : "Join Now"}
            </Link>
          </header>

          {/* headline + X-ray */}
          <div id="top" className="relative mx-auto flex w-full max-w-[1440px] flex-1 flex-col justify-center px-6 pb-10 pt-8 sm:px-12 lg:pt-4">
            <div className="relative mx-auto w-full lg:h-[420px]">
              <img src="/images/hero-xray.webp" alt="Chest X-ray"
                className="relative z-10 mx-auto w-[min(78vw,340px)] lg:absolute lg:left-1/2 lg:top-[-30px] lg:w-[460px] lg:-translate-x-1/2" />
              <h1 className="mt-[-56px] flex justify-between text-[16vw] font-medium leading-[0.85] tracking-[-0.04em] text-[#F4F4EF] lg:absolute lg:inset-x-0 lg:top-[110px] lg:mt-0 lg:text-[min(11.6vw,160px)]">
                <span>PNEUMO</span><span className="hidden lg:inline">SCOPE</span>
              </h1>
              <div className="mt-1 text-right text-[16vw] font-medium leading-[0.85] tracking-[-0.04em] text-[#F4F4EF] lg:hidden">SCOPE</div>
            </div>

            {/* sub-line under the headline */}
            <div className="relative z-20 mt-6 flex flex-col gap-3 text-[15px] text-white/90 sm:flex-row sm:items-center lg:mt-0">
              <span>Pneumonia detection with uncertainty.</span>
              <span className="hidden h-px flex-1 bg-white/40 sm:block" />
              <span className="hidden w-[420px] lg:block" />
              <span className="hidden h-px flex-1 bg-white/40 lg:block" />
              <span className="flex items-center gap-2">ResNet-50 <Activity className="h-4 w-4" style={{ color: ACCENT }} /> v1.1.0</span>
            </div>

            {/* CTA */}
            <div className="relative z-20 mt-8 flex justify-center lg:mt-[-10px]">
              <Link to={start} className="inline-flex items-center gap-2 rounded-full px-8 py-4 text-[17px] font-medium text-white shadow-[0_10px_30px_-8px_rgba(240,108,56,0.8)] transition hover:brightness-110"
                style={{ background: ACCENT }}>
                Analyse an X-ray <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            {/* bottom row */}
            <div className="relative z-20 mt-12 grid items-end gap-8 lg:mt-16 lg:grid-cols-[1fr_auto_1fr]">
              <div className="flex flex-col items-start">
                <div className="flex items-center gap-3">
                  <div className="flex -space-x-3">
                    {[1, 2, 3].map((i) => <img key={i} src={`/images/thumb-${i}.webp`} alt="" className="h-10 w-10 rounded-full border-2 border-[#1A1614] bg-black" />)}
                  </div>
                  <span className="text-[15px] font-medium">5,856 X-rays</span>
                </div>
                <span className="ml-[54px] mt-3 h-2 w-2 rounded-full bg-white" />
                <span className="ml-[57px] h-12 w-px bg-white/60" />
                <Pill className="mt-1">Know when to refer.</Pill>
              </div>

              <div className="flex items-stretch gap-4 rounded-3xl border border-white/10 bg-white/[0.06] p-3 backdrop-blur-md">
                <img src="/images/gradcam.webp" alt="Grad-CAM heatmap from the model" className="h-32 w-32 rounded-2xl object-cover sm:h-36 sm:w-40" />
                <div className="flex flex-col justify-between py-1 pr-3">
                  <div>
                    <div className="text-[44px] font-medium leading-none">95.3%</div>
                    <div className="mt-2 text-[14.5px] text-white/85">Test accuracy</div>
                  </div>
                  <div className="mt-3 flex items-center gap-4 text-[14px]">
                    <span>ResNet-50</span>
                    <span className="h-8 w-px bg-white/40" />
                    <span className="leading-tight text-white/90">0.988<br />ROC-AUC</span>
                  </div>
                </div>
              </div>

              <div className="flex flex-col items-start lg:items-end">
                <p className="text-[26px] leading-snug lg:text-right">Uncertainty-aware<br />triage</p>
                <span className="mt-3 h-10 w-px bg-white/60 lg:mr-[52px]" />
                <span className="h-2 w-2 rounded-full bg-white lg:mr-[48px]" />
                <div className="mt-3 flex h-[72px] w-[72px] items-center justify-center rounded-full border border-white/30 bg-gradient-to-br from-[#F9A26C] to-[#B84A20] shadow-[0_0_30px_rgba(240,108,56,0.55)] lg:mr-[16px]">
                  <ScanLine className="h-8 w-8 text-white" />
                </div>
                <a href="#how" className="mt-3 text-[15px] underline underline-offset-4 lg:mr-[10px]" style={{ color: ACCENT }}>Learn More</a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ===================== HOW IT WORKS ===================== */}
      <section id="how" className="mx-auto max-w-[1440px] px-6 pt-16 sm:px-12">
        <h2 className="text-[32px] font-medium tracking-tight text-white">How it works</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            [UploadCloud, "Upload", "Add a chest X-ray (JPG or PNG)."],
            [ScanLine, "Analyse", "Normal or Pneumonia, with a probability."],
            [HelpCircle, "Check", "Uncertain results are marked REFER."],
            [Eye, "Explain", "A heatmap shows what the model looked at."],
          ].map(([Icon, t, d], i) => {
            const I = Icon as typeof ScanLine;
            return (
              <div key={t as string} className="rounded-3xl border border-white/10 bg-white/[0.05] p-6 text-white backdrop-blur-md">
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/20"><I className="h-5 w-5" /></div>
                  <span className="text-[13px] text-white/70">0{i + 1}</span>
                </div>
                <div className="mt-5 text-[18px] font-medium">{t as string}</div>
                <p className="mt-1 text-[14px] text-white/80">{d as string}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ===================== RESULTS ===================== */}
      <section id="results" className="mx-auto max-w-[1440px] px-6 pt-14 sm:px-12">
        <h2 className="text-[32px] font-medium tracking-tight text-white">Results</h2>
        <p className="mt-1 text-[15px] text-white/80">Tested on 837 X-rays from patients not seen in training.</p>
        <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[["95.3%", "Accuracy"], ["96.2%", "Recall"], ["0.988", "ROC-AUC"], ["98.6%", "Accuracy on AUTO results"]].map(([v, l]) => (
            <div key={l} className="rounded-3xl border border-white/10 bg-white/[0.05] px-6 py-6 text-white backdrop-blur-md">
              <div className="text-[36px] font-medium leading-none">{v}</div>
              <div className="mt-2 text-[14px] text-white/80">{l}</div>
            </div>
          ))}
        </div>
        <div className="mt-10 flex flex-col items-start justify-between gap-5 rounded-[32px] border border-white/10 bg-gradient-to-r from-[#3A2216]/90 to-[#15110F]/90 px-8 py-10 text-white backdrop-blur-xl sm:flex-row sm:items-center">
          <div>
            <div className="text-[26px] font-medium">Try it with your own X-ray</div>
            <div className="mt-1 text-white/75">Results in about a second.</div>
          </div>
          <Link to={start} className="inline-flex items-center gap-2 rounded-full px-7 py-3.5 text-[16px] font-medium text-white shadow-[0_10px_30px_-8px_rgba(240,108,56,0.8)]" style={{ background: ACCENT }}>
            Get started <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <footer className="mx-auto mt-14 flex max-w-[1440px] flex-col gap-2 px-6 pb-8 sm:px-12 text-[13px] text-white/80 sm:flex-row sm:justify-between sm:px-4">
        <span>PneumoScope · Academic project</span>
        <span>X-ray images: Kermany et al., CC BY 4.0</span>
      </footer>
      </div>
    </div>
  );
}
