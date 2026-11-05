import { useEffect, useState } from "react";
import { Crown, Lock, RotateCcw, Snowflake, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { Switch } from "@/components/ui/switch";
import { api, formatErr } from "@/lib/api";
import ArenaQuestions from "@/pages/admin/ArenaQuestions";

const toLocal = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
const fromLocal = (v) => (v ? new Date(v).toISOString().replace("Z", "+00:00") : null);

function SettingsCard({ s, reload }) {
  const [f, setF] = useState({ starts_at: toLocal(s.starts_at), closes_at: toLocal(s.closes_at), prize: s.prize, announcement: s.announcement });
  const save = async (e) => {
    e.preventDefault();
    try { await api.put("/arena/admin/settings", { ...f, starts_at: fromLocal(f.starts_at), closes_at: fromLocal(f.closes_at) }); toast.success("Arena settings saved"); reload(); }
    catch (err) { toast.error(formatErr(err)); }
  };
  return (
    <form onSubmit={save} className="glass-strong space-y-4 rounded-3xl p-6" data-testid="arena-admin-settings-form">
      <p className="eyebrow">Arena settings</p>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label><span className="field-label">Opens at (blank = open now)</span><input type="datetime-local" className="field" value={f.starts_at} onChange={(e) => setF({ ...f, starts_at: e.target.value })} data-testid="arena-admin-starts-input" /></label>
        <label><span className="field-label">Closes at</span><input type="datetime-local" className="field" value={f.closes_at} onChange={(e) => setF({ ...f, closes_at: e.target.value })} data-testid="arena-admin-closes-input" /></label>
      </div>
      <label className="block"><span className="field-label">Champion prize description</span><input className="field" placeholder="e.g. Goodies hamper + certificate" value={f.prize} onChange={(e) => setF({ ...f, prize: e.target.value })} data-testid="arena-admin-prize-input" /></label>
      <label className="block"><span className="field-label">Winner announcement message</span><textarea className="field min-h-[80px]" value={f.announcement} onChange={(e) => setF({ ...f, announcement: e.target.value })} data-testid="arena-admin-announcement-input" /></label>
      <button className="btn-neon" data-testid="arena-admin-save-settings">Save settings</button>
    </form>
  );
}

function ControlCard({ s, reload, participants }) {
  const [tie, setTie] = useState(null);
  const act = async (fn, msg) => { try { await fn(); toast.success(msg); reload(); } catch (e) { toast.error(formatErr(e)); } };
  const finalize = async (champion_user_id) => {
    try {
      const { data } = await api.post("/arena/admin/finalize", { champion_user_id });
      if (data.tie) { setTie(data.candidates); toast.warning("Tie at #1 — choose the champion after review"); }
      else { setTie(null); toast.success(`${data.champion.name} is the Arena Champion`); }
      reload();
    } catch (e) { toast.error(formatErr(e)); }
  };
  const tied = tie || (s.tie_candidates?.length ? participants.filter((p) => s.tie_candidates.includes(p.user_id)) : null);
  return (
    <div className="glass-strong space-y-5 rounded-3xl p-6" data-testid="arena-admin-control">
      <div className="flex items-center justify-between"><p className="eyebrow">Competition control</p><span className="font-mono text-[10px] uppercase tracking-[0.25em] text-neon" data-testid="arena-admin-status">{s.status}</span></div>
      <div className="flex flex-wrap gap-3">
        {s.frozen ? <button onClick={() => act(() => api.post("/arena/admin/freeze", { value: false }), "Scoring unfrozen")} className="btn-ghost" disabled={s.finalized} data-testid="arena-admin-unfreeze"><Snowflake size={15} /> Unfreeze</button>
          : <button onClick={() => act(() => api.post("/arena/admin/freeze", { value: true }), "Scoring frozen")} className="btn-ghost" data-testid="arena-admin-freeze"><Lock size={15} /> Freeze scoring</button>}
        {!s.finalized && <button onClick={() => finalize(null)} className="btn-neon" data-testid="arena-admin-finalize"><Crown size={15} /> Finalise winner</button>}
        {s.finalized && <button onClick={() => window.confirm("Reopen the Arena? This removes the champion and unfreezes scoring.") && act(() => api.post("/arena/admin/reopen"), "Arena reopened")} className="btn-ghost" data-testid="arena-admin-reopen"><RotateCcw size={15} /> Reopen</button>}
      </div>
      {s.champion && <p className="text-sm text-white/75" data-testid="arena-admin-champion">Champion: <span className="text-[#FFCF5A]">{s.champion.name}</span> · {s.champion.xp} XP{s.champion.tie_resolved_by_admin && " · tie resolved by admin"}</p>}
      {tied && !s.finalized && (
        <div className="rounded-2xl border border-neon/50 bg-neon/10 p-4" data-testid="arena-admin-tie-review">
          <p className="flex items-center gap-2 text-sm text-neon"><ShieldAlert size={15} /> Tie after all tie-breakers. Review and declare the champion:</p>
          <div className="mt-3 space-y-2">{tied.map((c) => (
            <div key={c.user_id} className="flex items-center justify-between gap-3 text-sm text-white/80">
              <span>{c.name} · {c.xp} XP · {c.completed} done</span>
              <button onClick={() => finalize(c.user_id)} className="btn-ghost !px-4 !py-1.5 !text-[10px]" data-testid={`arena-admin-pick-${c.user_id}`}>Declare</button>
            </div>))}
          </div>
        </div>
      )}
      <p className="text-xs text-white/40">Freezing stops all XP instantly. Finalising requires a frozen or closed Arena and computes the champion from verified results.</p>
    </div>
  );
}

function Participants({ rows, reload }) {
  const dq = async (p, v) => { try { await api.post(`/arena/admin/participants/${p.user_id}/disqualify`, { value: v }); toast.success(v ? "Excluded from leaderboard" : "Reinstated"); reload(); } catch (e) { toast.error(formatErr(e)); } };
  if (!rows.length) return <p className="glass rounded-3xl p-8 text-center text-white/50">No participant activity yet.</p>;
  return (
    <div className="glass overflow-x-auto rounded-3xl" data-testid="arena-admin-participants">
      <table className="w-full min-w-[820px] text-left text-sm">
        <thead><tr className="border-b border-white/10 font-mono text-[10px] uppercase tracking-[0.25em] text-white/40">
          <th className="px-5 py-4">Rank</th><th className="px-4 py-4">Participant</th><th className="px-4 py-4">XP</th><th className="px-4 py-4">Done</th><th className="px-4 py-4">Accuracy</th><th className="px-4 py-4">Flags</th><th className="px-5 py-4">Excluded</th>
        </tr></thead>
        <tbody>{rows.map((p) => (
          <tr key={p.user_id} className={`border-b border-white/5 ${p.flags.length ? "bg-neon/[0.06]" : ""}`} data-testid={`arena-admin-participant-${p.user_id}`}>
            <td className="px-5 py-3 font-mono text-white/60">{p.disqualified ? "—" : p.rank}</td>
            <td className="px-4 py-3 text-white">{p.name}<p className="text-xs text-white/40">{p.team_name}</p></td>
            <td className="px-4 py-3 font-mono text-ice">{p.xp}</td>
            <td className="px-4 py-3 font-mono text-white/70">{p.completed}</td>
            <td className="px-4 py-3 font-mono text-white/70">{p.accuracy}% <span className="text-white/35">({p.attempts})</span></td>
            <td className="px-4 py-3 text-xs text-neon">{p.flags.length ? p.flags.join(" · ") : <span className="text-white/30">—</span>}</td>
            <td className="px-5 py-3"><Switch checked={p.disqualified} onCheckedChange={(v) => dq(p, v)} data-testid={`arena-admin-dq-${p.user_id}`} /></td>
          </tr>))}
        </tbody>
      </table>
    </div>
  );
}

export default function ArenaAdmin() {
  const [s, setS] = useState(null);
  const [parts, setParts] = useState([]);
  const load = async () => {
    const [a, b] = await Promise.all([api.get("/arena/admin/settings"), api.get("/arena/admin/participants")]);
    setS(a.data); setParts(b.data);
  };
  useEffect(() => { load().catch((e) => toast.error(formatErr(e))); }, []);
  if (!s) return <p className="text-white/40">Loading Arena controls…</p>;
  return (
    <div className="space-y-6" data-testid="arena-admin">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <SettingsCard key={`${s.starts_at}${s.closes_at}${s.prize}`} s={s} reload={load} />
        <ControlCard s={s} reload={load} participants={parts} />
      </div>
      <p className="eyebrow">Participants & suspicious activity</p>
      <Participants rows={parts} reload={load} />
      <ArenaQuestions />
    </div>
  );
}
