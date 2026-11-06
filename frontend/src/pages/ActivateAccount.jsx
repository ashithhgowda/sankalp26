import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { useAuth, homeFor } from "@/context/AuthContext";
import { api, formatErr } from "@/lib/api";
import { Wordmark } from "@/components/Wordmark";

export default function ActivateAccount() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [info, setInfo] = useState(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const { activate } = useAuth();
  const nav = useNavigate();
  useEffect(() => {
    api.post("/auth/invitations/inspect", { token }).then(({ data }) => setInfo(data)).catch((e) => setInfo({ error: formatErr(e) }));
  }, [token]);
  const submit = async (event) => {
    event.preventDefault();
    if (info.purpose !== "verify_email" && password !== confirm) return toast.error("Passwords do not match");
    setBusy(true);
    try {
      const user = await activate({ token, password: info.purpose === "verify_email" ? null : password });
      toast.success("Account activated securely"); nav(homeFor(user.role));
    } catch (error) { toast.error(formatErr(error)); } finally { setBusy(false); }
  };
  return <main className="grain flex min-h-screen items-center justify-center bg-jet px-5 py-16" data-testid="activate-account-page">
    <section className="glass-strong glow-border w-full max-w-lg rounded-3xl p-8 sm:p-10">
      <Wordmark className="text-3xl" testid="activate-wordmark" />
      {!info ? <p className="mt-8 text-white/60" data-testid="activate-loading">Checking your private link…</p> : info.error ? <div className="mt-8" data-testid="activate-error"><p className="text-neon">{info.error}</p><Link to="/auth" className="btn-ghost mt-6" data-testid="activate-login-link">Return to login</Link></div> :
        <form onSubmit={submit} className="mt-8 space-y-5" data-testid="activate-account-form">
          <ShieldCheck className="text-ice" />
          <div><p className="eyebrow">Secure activation</p><h1 className="mt-2 font-editorial text-3xl font-bold uppercase text-white">Welcome, {info.name}</h1><p className="mt-2 text-sm text-white/55">{info.email_hint}</p></div>
          {info.purpose !== "verify_email" && <label><span className="field-label">Create your private password</span><input type="password" minLength={12} required className="field" value={password} onChange={(e) => setPassword(e.target.value)} data-testid="activate-password-input" /><span className="mt-2 block text-xs text-white/40">12+ characters with upper, lower, number and symbol.</span></label>}
          {info.purpose !== "verify_email" && <label><span className="field-label">Confirm your password</span><input type="password" minLength={12} required className="field" value={confirm} onChange={(e) => setConfirm(e.target.value)} data-testid="activate-confirm-password-input" /></label>}
          <button className="btn-neon w-full" disabled={busy} data-testid="activate-submit-button">{busy ? <Loader2 className="animate-spin" /> : <><CheckCircle2 /> Activate account</>}</button>
        </form>}
    </section>
  </main>;
}