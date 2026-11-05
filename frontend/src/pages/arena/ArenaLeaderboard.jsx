import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Crown, Search } from "lucide-react";
import DashShell from "@/components/DashShell";
import ChampionCard from "@/components/arena/ChampionCard";
import { ArenaNav, BadgeChip, StatusPill, useArena } from "@/components/arena/arenaKit";
import { ArenaTitle } from "@/pages/arena/ArenaHome";
import { api } from "@/lib/api";

const MEDALS = { 1: ["#FFCF5A", "Gold"], 2: ["#D7DEE8", "Silver"], 3: ["#E08A4F", "Bronze"] };
const LABEL = { live: "Provisional standings", upcoming: "Provisional standings", closed: "Closed — awaiting final verification", final: "Final standings" };

export default function ArenaLeaderboard() {
  const { state, user } = useArena();
  const [data, setData] = useState(null);
  const [q, setQ] = useState("");

  useEffect(() => {
    const load = () => api.get("/arena/leaderboard").then((r) => setData(r.data)).catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  const rows = useMemo(() => (data?.rows || []).filter((r) => `${r.name} ${r.team_name}`.toLowerCase().includes(q.toLowerCase())), [data, q]);
  const badgeMeta = Object.fromEntries((state?.badges || []).map((b) => [b.key, b]));
  const top = (data?.rows || []).filter((r) => r.rank <= 3).slice(0, 3);
  const leader = data?.rows?.[0];

  return (
    <DashShell eyebrow="Arena // individual XP leaderboard" title={<ArenaTitle />} actions={data && <StatusPill status={data.status} />}>
      <ArenaNav />
      {data?.champion && <ChampionCard champion={data.champion} prize={data.prize} announcement={data.announcement} />}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <p className="font-mono text-[11px] uppercase tracking-[0.25em] text-white/60" data-testid="arena-board-state">{data ? LABEL[data.status] : "Loading…"} · live every 5s</p>
        {leader && <p className="flex items-center gap-2 text-sm text-white/70" data-testid="arena-current-leader"><Crown size={15} className="text-[#FFCF5A]" /> Current leader: <span className="text-white">{leader.name}</span> · {leader.xp} XP</p>}
      </div>

      {top.length > 0 && (
        <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          {top.map((r, i) => {
            const [c, label] = MEDALS[r.rank] || MEDALS[3];
            return (
              <motion.div key={r.user_id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }} data-testid={`arena-podium-${r.rank}`}
                className="glass-strong relative overflow-hidden rounded-3xl p-6" style={{ border: `1px solid ${c}66`, boxShadow: `0 0 50px -20px ${c}` }}>
                <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full blur-[70px]" style={{ background: `${c}33` }} />
                <p className="font-mono text-[10px] uppercase tracking-[0.3em]" style={{ color: c }}>{label} · #{r.rank}</p>
                <p className="mt-3 font-display text-2xl font-bold uppercase tracking-wide text-white">{r.name}</p>
                <p className="text-xs text-white/45">{r.team_name || "—"}</p>
                <p className="mt-4 font-wordmark text-4xl font-black" style={{ color: c }}>{r.xp} <span className="text-base text-white/40">XP</span></p>
              </motion.div>
            );
          })}
        </div>
      )}

      <label className="relative mb-5 block max-w-md">
        <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
        <input className="field !pl-11" placeholder="Search participants" value={q} onChange={(e) => setQ(e.target.value)} data-testid="arena-board-search" />
      </label>

      {rows.length === 0 ? <p className="glass rounded-3xl p-10 text-center text-white/50" data-testid="arena-board-empty">{data?.rows?.length ? "No participants match your search." : "No XP earned yet. The board is waiting for its first legend."}</p> : (
        <div className="glass overflow-x-auto rounded-3xl" data-testid="arena-board-table">
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead><tr className="border-b border-white/10 font-mono text-[10px] uppercase tracking-[0.25em] text-white/40">
              <th className="px-6 py-4">Rank</th><th className="px-4 py-4">Participant</th><th className="px-4 py-4">Team</th><th className="px-4 py-4">Completed</th><th className="px-4 py-4">Badges</th><th className="px-6 py-4 text-right">XP</th>
            </tr></thead>
            <tbody>
              {rows.map((r) => {
                const mine = user && r.user_id === user.id;
                const medal = MEDALS[r.rank];
                return (
                  <tr key={r.user_id} data-testid={`arena-board-row-${r.rank}`} className={`border-b border-white/5 transition-colors ${mine ? "bg-neon/10" : "hover:bg-white/[0.03]"}`}>
                    <td className="px-6 py-4 font-wordmark text-lg font-black" style={{ color: medal ? medal[0] : "rgba(255,255,255,.6)" }}>{String(r.rank).padStart(2, "0")}</td>
                    <td className="px-4 py-4 text-white">{r.name} {mine && <span className="ml-2 rounded-full border border-neon/60 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.2em] text-neon" data-testid="arena-board-you">You</span>}</td>
                    <td className="px-4 py-4 text-white/55">{r.team_name || "—"}</td>
                    <td className="px-4 py-4 font-mono text-white/70">{r.completed}</td>
                    <td className="px-4 py-4"><div className="flex flex-wrap gap-1">{r.badges.map((b) => badgeMeta[b] && <BadgeChip key={b} badge={badgeMeta[b]} size="sm" />)}</div></td>
                    <td className="px-6 py-4 text-right font-wordmark text-xl font-black text-grad">{r.xp}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-5 text-xs text-white/40" data-testid="arena-tiebreak-rules">Ranking: total XP, then most challenges completed, then whoever reached their final score first. Players identical on all three share a rank and are reviewed by the organisers. Standings are calculated only from verified, server-checked answers.</p>
    </DashShell>
  );
}
