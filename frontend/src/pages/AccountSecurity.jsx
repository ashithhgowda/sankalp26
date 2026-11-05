import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Loader2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { useAuth, homeFor } from "@/context/AuthContext";
import { formatErr } from "@/lib/api";
import { Wordmark } from "@/components/Wordmark";

export default function AccountSecurity() {
  const { user, changePassword, logout } = useAuth();
  const [form, setForm] = useState({ current_password: "", new_password: "", confirm: "" });
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  if (user === null) return null;
  if (!user) return <Navigate to="/auth" replace />;
  const submit = async (event) => {
    event.preventDefault();
    if (form.new_password !== form.confirm) return toast.error("New passwords do not match");
    setBusy(true);
    try { const updated = await changePassword(form); toast.success("Password changed. Previous sessions were closed."); nav(homeFor(updated.role)); }
    catch (error) { toast.error(formatErr(error)); } finally { setBusy(false); }
  };
  return <main className="grain flex min-h-screen items-center justify-center bg-jet px-5 py-16" data-testid="account-security-page">
    <section className="glass-strong glow-border w-full max-w-lg rounded-3xl p-8 sm:p-10">
      <Wordmark className="text-3xl" testid="security-wordmark" />
      <ShieldCheck className="mt-8 text-ice" /><p className="eyebrow mt-4">Account security</p>
      <h1 className="mt-2 font-editorial text-3xl font-bold uppercase text-white">{user.must_change_password ? "Replace your initial password" : "Change password"}</h1>
      <p className="mt-3 text-sm text-white/55">Choose a unique 12+ character password. Changing it closes every previous session.</p>
      <form onSubmit={submit} className="mt-7 space-y-4" data-testid="change-password-form">
        <input className="field" type="password" required placeholder="Current password" value={form.current_password} onChange={(e) => setForm({ ...form, current_password: e.target.value })} data-testid="current-password-input" />
        <input className="field" type="password" minLength={12} required placeholder="New password" value={form.new_password} onChange={(e) => setForm({ ...form, new_password: e.target.value })} data-testid="new-password-input" />
        <input className="field" type="password" minLength={12} required placeholder="Confirm new password" value={form.confirm} onChange={(e) => setForm({ ...form, confirm: e.target.value })} data-testid="confirm-password-input" />
        <button className="btn-neon w-full" disabled={busy} data-testid="change-password-submit-button">{busy ? <Loader2 className="animate-spin" /> : "Secure my account"}</button>
      </form>
      {!user.must_change_password && <button onClick={async () => { try { await logout(); nav("/"); } catch (error) { toast.error(formatErr(error)); } }} className="btn-ghost mt-4 w-full" data-testid="security-logout-button">Sign out</button>}
    </section>
  </main>;
}