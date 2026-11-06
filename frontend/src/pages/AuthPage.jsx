import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Wordmark, LogoBars } from "@/components/Wordmark";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth, homeFor } from "@/context/AuthContext";
import { usePublicConfig } from "@/context/PublicConfigContext";
import { api, formatErr } from "@/lib/api";
import { IMAGES } from "@/data/content";

const Field = ({ label, id, ...p }) => (
  <label className="block">
    <span className="field-label">{label}</span>
    <input className="field" data-testid={id} {...p} />
  </label>
);

// ─── Login ────────────────────────────────────────────────────────────────────
function LoginForm() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ email: "", password: "" });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const u = await login(f.email, f.password);
      toast.success(`Welcome back, ${u.team_name || u.name}`);
      nav(homeFor(u.role));
    } catch (err) {
      toast.error(formatErr(err));
    } finally {
      setBusy(false);
    }
  };

  const resend = async () => {
    if (!f.email) return toast.error("Enter your registered email first");
    try {
      const { data } = await api.post("/auth/resend-activation", { email: f.email });
      toast.success(data.message);
    } catch (error) {
      toast.error(formatErr(error));
    }
  };

  return (
    <form onSubmit={submit} className="space-y-5" data-testid="login-form">
      <Field
        label="Email"
        id="login-email-input"
        type="email"
        required
        autoComplete="email"
        value={f.email}
        onChange={(e) => setF({ ...f, email: e.target.value })}
        placeholder="leader@college.edu"
      />
      <Field
        label="Password"
        id="login-password-input"
        type="password"
        required
        autoComplete="current-password"
        value={f.password}
        onChange={(e) => setF({ ...f, password: e.target.value })}
        placeholder="••••••••"
      />
      <button disabled={busy} className="btn-neon w-full" data-testid="login-submit-button">
        {busy ? <Loader2 className="animate-spin" size={16} /> : <>Enter the grid <ArrowRight size={16} /></>}
      </button>
      <p className="text-center font-mono text-[10px] uppercase tracking-[0.25em] text-white/40">
        Teams, members, judges &amp; admins sign in here
      </p>
      <Link
        to="/forgot-password"
        data-testid="auth-forgot-password-link"
        className="block text-center text-sm text-ice hover:underline"
      >
        Forgot password?
      </Link>
      <button
        type="button"
        onClick={resend}
        data-testid="auth-resend-activation-button"
        className="block w-full text-center text-xs text-white/45 hover:text-ice"
      >
        Resend an account activation link
      </button>
    </form>
  );
}

// ─── Register ─────────────────────────────────────────────────────────────────
const emptyMember = { name: "", usn: "", email: "", college: "" };

function RegisterForm() {
  const { register } = useAuth();
  const { topics, portals } = usePublicConfig();
  const nav = useNavigate();
  const [f, setF] = useState({
    team_name: "", college: "", name: "", usn: "",
    email: "", phone: "", password: "", topic_id: "",
  });
  const [members, setMembers] = useState([{ ...emptyMember }, { ...emptyMember }]);
  const [busy, setBusy] = useState(false);

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const setM = (i, k) => (e) =>
    setMembers(members.map((m, j) => (j === i ? { ...m, [k]: e.target.value } : m)));
  const memberDetailsStarted = (member) =>
    Boolean(member.name.trim() || member.usn.trim() || member.email.trim() || member.college.trim());

  const submit = async (e) => {
    e.preventDefault();
    if (!f.topic_id) return toast.error("Choose a challenge topic");
    setBusy(true);
    try {
      const u = await register({ ...f, members });
      toast.success(
        `Welcome to SANKALP'26! Team "${u.team_name || f.team_name}" registered successfully.`
      );
      nav(homeFor(u.role));
    } catch (err) {
      toast.error(formatErr(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-5" data-testid="register-form">
      {/* Leader details */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Field
          label="Team name"
          id="register-team-name-input"
          required
          value={f.team_name}
          onChange={set("team_name")}
          placeholder="Neon Circuit"
        />
        <Field
          label="College"
          id="register-college-input"
          required
          value={f.college}
          onChange={set("college")}
          placeholder="AJIET, Mangaluru"
        />
        <Field
          label="Team leader name"
          id="register-leader-name-input"
          required
          autoComplete="name"
          value={f.name}
          onChange={set("name")}
        />
        <Field
          label="Leader USN"
          id="register-leader-usn-input"
          required
          value={f.usn}
          onChange={set("usn")}
          placeholder="4AJ21EC001"
        />
        <Field
          label="Leader phone"
          id="register-phone-input"
          required
          type="tel"
          autoComplete="tel"
          value={f.phone}
          onChange={set("phone")}
          placeholder="+91 9XXXXXXXXX"
        />
        <Field
          label="Leader email (login)"
          id="register-email-input"
          type="email"
          required
          autoComplete="email"
          value={f.email}
          onChange={set("email")}
        />
        <div className="sm:col-span-2">
          <Field
            label="Password (12+ characters)"
            id="register-password-input"
            type="password"
            minLength={12}
            required
            autoComplete="new-password"
            value={f.password}
            onChange={set("password")}
            placeholder="Uppercase, lowercase, number, symbol"
          />
        </div>
      </div>

      {/* Challenge theme — Radix Select renders via Portal so it's never clipped */}
      <div>
        <span className="field-label">Challenge theme</span>
        <Select value={f.topic_id} onValueChange={(v) => setF({ ...f, topic_id: v })}>
          <SelectTrigger className="field h-auto min-h-[44px]" data-testid="register-track-select">
            <SelectValue placeholder="Choose one of the six themes" />
          </SelectTrigger>
          <SelectContent
            className="border-white/10 bg-[#121214] text-white"
            style={{ zIndex: 9999 }}
            position="popper"
          >
            {topics.map((t, i) => (
              <SelectItem
                key={t.topic_id}
                value={t.topic_id}
                data-testid={`register-track-option-${t.topic_id}`}
                className="cursor-pointer py-3 text-sm"
              >
                {String(i + 1).padStart(2, "0")} · {t.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Optional member slots; a filled slot must identify one complete member. */}
      {members.map((m, i) => (
        <div key={i} className="rounded-2xl border border-white/10 bg-white/[0.02] p-4">
          <p className="mb-3 font-mono text-[10px] uppercase tracking-[0.3em] text-ice">
            Member {i + 2} · optional
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <input
              className="field"
              placeholder="Full name"
              required={memberDetailsStarted(m)}
              value={m.name}
              onChange={setM(i, "name")}
              data-testid={`register-member-${i + 2}-name-input`}
            />
            <input
              className="field"
              placeholder="USN"
              required={memberDetailsStarted(m)}
              value={m.usn}
              onChange={setM(i, "usn")}
              data-testid={`register-member-${i + 2}-usn-input`}
            />
            <input
              className="field"
              placeholder="Email"
              type="email"
              required={memberDetailsStarted(m)}
              value={m.email}
              onChange={setM(i, "email")}
              data-testid={`register-member-${i + 2}-email-input`}
            />
            <input
              className="field"
              placeholder="College (optional)"
              value={m.college}
              onChange={setM(i, "college")}
              data-testid={`register-member-${i + 2}-college-input`}
            />
          </div>
        </div>
      ))}

      <p className="text-xs leading-relaxed text-white/45">
        Leave a member slot blank if your team is smaller. Each listed member must provide a name, USN and unique email and will receive an account invitation.
      </p>

      <button
        disabled={busy || portals.application === false}
        className="btn-neon w-full"
        data-testid="register-submit-button"
      >
        {busy ? (
          <Loader2 className="animate-spin" size={16} />
        ) : portals.application === false ? (
          "Registrations closed"
        ) : (
          <>Register team <ArrowRight size={16} /></>
        )}
      </button>
    </form>
  );
}

// ─── Page wrapper ─────────────────────────────────────────────────────────────
export default function AuthPage() {
  const [params, setParams] = useSearchParams();
  const mode = params.get("mode") === "register" ? "register" : "login";

  return (
    <div
      className="grain relative grid min-h-screen grid-cols-1 bg-jet lg:grid-cols-[1fr_1.1fr]"
      data-testid="auth-page"
    >
      {/* Left decorative panel — desktop only */}
      <div className="relative hidden overflow-hidden lg:block">
        <motion.img
          src={IMAGES.heroGirl}
          alt=""
          initial={{ scale: 1.15 }}
          animate={{ scale: 1 }}
          transition={{ duration: 2 }}
          className="absolute inset-0 h-full w-full object-cover object-top"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-jet/30 to-jet" />
        <div className="absolute inset-0 bg-gradient-to-t from-jet via-transparent to-transparent" />
        <div className="scanline" />
        <div className="absolute bottom-12 left-12 right-12">
          <Wordmark className="text-6xl" testid="auth-wordmark" />
          <LogoBars className="mt-4 max-w-sm" />
          <p className="mt-5 font-display text-sm uppercase text-white/70 spaced">
            Build. Breakthrough. <span className="text-neon">Belong.</span>
          </p>
        </div>
      </div>

      {/* Right form panel */}
      <div className="relative flex min-h-screen items-start justify-center px-4 py-12 sm:items-center sm:px-10 sm:py-14">
        <div className="absolute right-0 top-0 h-96 w-96 rounded-full bg-neon/15 blur-[140px]" />
        <div className="absolute bottom-0 left-0 h-96 w-96 rounded-full bg-cerulean/20 blur-[140px]" />

        <div className="relative w-full max-w-xl">
          <Link
            to="/"
            className="mb-6 inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.25em] text-white/50 hover:text-white sm:mb-8"
            data-testid="auth-back-link"
          >
            <ArrowLeft size={14} /> Back to site
          </Link>

          {/*
            overflow: visible is required so the Radix Select portal is not
            clipped by the card on iOS Safari / WebKit browsers.
          */}
          <div
            className="glass-strong glow-border rounded-[2rem] p-6 sm:p-10"
            style={{ overflow: "visible" }}
          >
            <p className="eyebrow mb-3">
              {{ login: "Access terminal", register: "Team registration" }[mode]}
            </p>
            <h1 className="font-editorial text-2xl font-extrabold uppercase text-white sm:text-3xl lg:text-4xl">
              {{ login: "Welcome back.", register: "Join the resolve." }[mode]}
            </h1>

            {/* Login / Register tab switcher */}
            <div className="my-6 grid grid-cols-2 rounded-full border border-white/10 bg-white/[0.03] p-1 sm:my-7">
              {["login", "register"].map((m) => (
                <button
                  key={m}
                  type="button"
                  data-testid={`auth-tab-${m}`}
                  onClick={() => setParams({ mode: m })}
                  className={`relative rounded-full py-2.5 font-mono text-[11px] uppercase tracking-[0.25em] transition-colors ${
                    mode === m ? "text-white" : "text-white/40"
                  }`}
                >
                  {mode === m && (
                    <motion.span
                      layoutId="authpill"
                      className="absolute inset-0 rounded-full bg-gradient-to-r from-cerulean to-neon"
                    />
                  )}
                  <span className="relative">{m}</span>
                </button>
              ))}
            </div>

            <AnimatePresence mode="wait">
              <motion.div
                key={mode}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.3 }}
              >
                {mode === "login" ? <LoginForm /> : <RegisterForm />}
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
