import { Loader2, Lock, Mail, User as UserIcon } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Logo } from "../components/Logo";
import { useAuth } from "../context/AuthContext";
import { errorMessage } from "../services/api";

function GlassInput({ id, type = "text", placeholder, value, onChange, icon, autoComplete }: {
  id: string; type?: string; placeholder: string; value: string; onChange: (v: string) => void; icon: ReactNode; autoComplete?: string;
}) {
  return (
    <div className="relative">
      <label htmlFor={id} className="sr-only">{placeholder}</label>
      <input id={id} type={type} placeholder={placeholder} value={value} autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-full border border-white/25 bg-white/[0.06] py-3 pl-5 pr-12 text-[14.5px] text-white placeholder:text-white/70 outline-none transition focus:border-[#F06C38] focus:bg-white/10 focus:ring-2 focus:ring-[#F06C38]/30" />
      <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-white/90">{icon}</span>
    </div>
  );
}

export default function LoginPage() {
  const { user, login, register } = useAuth();
  const nav = useNavigate();
  const loc = useLocation() as { state?: { from?: string } };
  const [params] = useSearchParams();
  const [mode, setMode] = useState<"login" | "register">(params.get("mode") === "register" ? "register" : "login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [showReset, setShowReset] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  function switchMode(m: "login" | "register") { setMode(m); setError(null); setShowReset(false); }

  function validate(): string | null {
    if (mode === "register" && name.trim().length < 2) return "Please enter your name.";
    if (!/^\S+@\S+\.\S+$/.test(email)) return "Please enter a valid email address.";
    if (!password) return "Please enter your password.";
    if (mode === "register" && (password.length < 8 || !/[A-Za-z]/.test(password) || !/\d/.test(password)))
      return "Password needs 8+ characters with a letter and a number.";
    return null;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const v = validate();
    if (v) return setError(v);
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await login(email.trim(), password, remember);
      else await register(name.trim(), email.trim(), password);
      nav(loc.state?.from ?? "/dashboard", { replace: true });
    } catch (err) {
      setError(errorMessage(err, mode === "login" ? "Sign-in failed." : "Could not create the account."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative min-h-screen bg-[#0B0908]">
      {/* full-screen X-ray background */}
      <div className="pointer-events-none fixed inset-0 bg-cover bg-center" style={{ backgroundImage: "url(/images/login-bg.webp)" }} aria-hidden />
      <div className="pointer-events-none fixed inset-0 bg-gradient-to-br from-black/45 via-black/15 to-black/65" aria-hidden />
      <div className="relative flex min-h-screen w-full flex-col">

        <div className="relative flex items-center justify-between px-6 py-6 sm:px-12">
          <Logo inverted />
          <Link to="/" className="rounded-full border border-white/20 bg-white/[0.06] px-4 py-1.5 text-[13px] text-white backdrop-blur-md hover:bg-white/15">
            ← Home
          </Link>
        </div>

        <div className="relative flex flex-1 items-center justify-center px-4 pb-10">
          <form onSubmit={submit} noValidate
            className="w-full max-w-[380px] rounded-[28px] border border-white/20 bg-[#1A1613]/45 px-8 py-9 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.8)] backdrop-blur-xl">
            <h1 className="text-center text-[28px] font-semibold text-white">{mode === "login" ? "Login" : "Register"}</h1>

            <div className="mt-7 space-y-4">
              {mode === "register" && (
                <GlassInput id="name" placeholder="Full name" value={name} onChange={setName} autoComplete="name" icon={<UserIcon className="h-4 w-4" />} />
              )}
              <GlassInput id="email" type="email" placeholder="Email ID" value={email} onChange={setEmail} autoComplete="email" icon={<Mail className="h-4 w-4" />} />
              <GlassInput id="password" type="password" placeholder="Password" value={password} onChange={setPassword}
                autoComplete={mode === "login" ? "current-password" : "new-password"} icon={<Lock className="h-4 w-4" />} />
            </div>

            {mode === "login" ? (
              <div className="mt-4 flex items-center justify-between text-[12.5px] text-white">
                <label className="flex cursor-pointer items-center gap-2">
                  <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="h-3.5 w-3.5 accent-[#F06C38]" />
                  Remember me
                </label>
                <button type="button" className="hover:underline" onClick={() => setShowReset((s) => !s)}>Forgot Password?</button>
              </div>
            ) : (
              <p className="mt-3 px-2 text-[12px] text-white/85">Password: 8+ characters with a letter and a number.</p>
            )}

            {showReset && mode === "login" && (
              <p className="mt-3 rounded-2xl bg-white/10 px-4 py-2.5 text-[12.5px] text-white">
                Please ask the administrator to reset your password.
              </p>
            )}
            {error && <p role="alert" className="mt-4 rounded-2xl bg-[#A1463C]/85 px-4 py-2.5 text-[13px] text-white">{error}</p>}

            <button disabled={busy}
              className="mt-6 flex w-full items-center justify-center gap-2 rounded-full bg-[#F06C38] py-3 text-[15px] font-semibold text-white shadow-[0_10px_30px_-8px_rgba(240,108,56,0.8)] transition hover:brightness-110 disabled:opacity-70">
              {busy && <Loader2 className="h-4 w-4 animate-spin" />}{mode === "login" ? "Login" : "Create account"}
            </button>

            <p className="mt-5 text-center text-[13px] text-white/90">
              {mode === "login" ? "Don't have an account? " : "Already have an account? "}
              <button type="button" className="font-semibold text-[#F9A26C] hover:underline" onClick={() => switchMode(mode === "login" ? "register" : "login")}>
                {mode === "login" ? "Register" : "Login"}
              </button>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
