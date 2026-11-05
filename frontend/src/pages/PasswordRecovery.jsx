import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api, formatErr } from "@/lib/api";
import { Wordmark } from "@/components/Wordmark";

export default function PasswordRecovery({ mode }) {
  const [params] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const submit = async (event) => {
    event.preventDefault();
    if (mode === "reset" && password !== confirm) return toast.error("Passwords do not match");
    setBusy(true);
    try {
      if (mode === "forgot") { const { data } = await api.post("/auth/forgot-password", { email }); toast.success(data.message); }
      else { await api.post("/auth/reset-password", { token: params.get("token"), password }); toast.success("Password reset. Sign in with your new password."); nav("/auth"); }
    } catch (error) {
      const retryAfter = Number(error?.response?.headers?.["retry-after"]);
      if (error?.response?.status === 429 && retryAfter > 0) {
        const minutes = Math.ceil(retryAfter / 60);
        toast.error(`Too many requests. Try again in about ${minutes} minute${minutes === 1 ? "" : "s"}.`);
      } else {
        toast.error(formatErr(error));
      }
    } finally { setBusy(false); }
  };
  return <main className="grain flex min-h-screen items-center justify-center bg-jet px-5 py-16" data-testid={`${mode}-password-page`}><section className="glass-strong w-full max-w-lg rounded-3xl p-8 sm:p-10">
    <Wordmark className="text-3xl" testid="recovery-wordmark" /><p className="eyebrow mt-8">Account recovery</p><h1 className="mt-2 font-editorial text-3xl font-bold uppercase text-white">{mode === "forgot" ? "Request reset link" : "Choose a new password"}</h1>
    <form onSubmit={submit} className="mt-7 space-y-4" data-testid={`${mode}-password-form`}>
      {mode === "forgot" ? <input className="field" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Registered email" data-testid="forgot-email-input" /> : <><input className="field" type="password" minLength={12} required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="New password" data-testid="reset-password-input" /><input className="field" type="password" minLength={12} required value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Confirm password" data-testid="reset-confirm-input" /></>}
      <button className="btn-neon w-full" disabled={busy} data-testid={`${mode}-password-submit-button`}>{busy ? <Loader2 className="animate-spin" /> : mode === "forgot" ? "Send secure link" : "Reset password"}</button>
    </form><Link to="/auth" className="mt-6 block text-center text-sm text-ice" data-testid="recovery-back-link">Back to login</Link>
  </section></main>;
}