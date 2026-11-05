import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Lock, Search } from "lucide-react";
import DashShell from "@/components/DashShell";
import LeaderboardTable from "@/components/LeaderboardTable";
import { api, formatErr } from "@/lib/api";
import { TRACKS } from "@/data/content";

export default function LeaderboardPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [retryVersion, setRetryVersion] = useState(0);
  const [q, setQ] = useState("");
  const [track, setTrack] = useState("all");

  useEffect(() => {
    let active = true;
    const load = () => api.get("/leaderboard")
      .then((r) => {
        if (active) {
          setData(r.data);
          setError(null);
        }
      })
      .catch((cause) => {
        if (active) setError(formatErr(cause));
      });
    load();
    const i = setInterval(load, 5000);
    return () => {
      active = false;
      clearInterval(i);
    };
  }, [retryVersion]);

  const rows = useMemo(() => (data?.rows || []).filter((r) =>
    (track === "all" || r.category === track) && `${r.team_name} ${r.title}`.toLowerCase().includes(q.toLowerCase())), [data, q, track]);

  const top = rows.slice(0, 3);

  return (
    <DashShell eyebrow="Live // refreshes every 5s" title={<>Real-time <span className="text-grad">leaderboard</span></>}
      actions={<span className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.3em] text-neon"><span className="pulse-dot h-2 w-2 rounded-full bg-neon" />Live</span>}>
      {error && <p className="mb-4 rounded-xl border border-neon/30 bg-neon/5 p-3 text-sm text-neon" role="alert">{error}</p>}
      {!data ? (
        <div className="glass mx-auto max-w-lg rounded-3xl p-8 text-center" data-testid="leaderboard-loading">
          <p className="text-white/60">{error ? "Leaderboard data could not be loaded." : "Loading leaderboard…"}</p>
          {error && <button className="btn-ghost mt-4" onClick={() => setRetryVersion((value) => value + 1)}>Retry</button>}
        </div>
      ) : data.hidden ? (
        <div className="glass mx-auto max-w-lg rounded-3xl p-12 text-center" data-testid="leaderboard-hidden">
          <Lock className="mx-auto text-neon" />
          <p className="mt-4 font-display text-xl font-bold uppercase tracking-wide text-white">Leaderboard sealed</p>
          <p className="mt-2 text-sm text-white/50">Rankings will be revealed by the organisers. Stay tuned.</p>
        </div>
      ) : (
        <>
          {top.length > 0 && (
            <div className="mb-8 grid grid-cols-1 gap-4 md:grid-cols-3">
              {top.map((r, i) => (
                <motion.div key={r.submission_id} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
                  className="glass glow-border rounded-3xl p-6" data-testid={`leaderboard-podium-${r.rank}`}>
                  <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-white/40">Rank {r.rank}</p>
                  <p className="mt-3 font-display text-2xl font-bold uppercase tracking-wide text-white">{r.team_name}</p>
                  <p className="text-xs text-white/45">{r.title}</p>
                  <p className="mt-4 font-wordmark text-4xl font-black text-grad">{r.score}</p>
                </motion.div>
              ))}
            </div>
          )}
          <div className="mb-5 flex flex-wrap gap-3">
            <label className="relative flex-1">
              <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" />
              <input className="field !pl-11" placeholder="Search teams or projects" value={q} onChange={(e) => setQ(e.target.value)} data-testid="leaderboard-search-input" />
            </label>
            <select className="field max-w-xs" value={track} onChange={(e) => setTrack(e.target.value)} data-testid="leaderboard-track-filter">
              <option value="all" className="bg-jet">All challenges</option>
              {TRACKS.map((t) => <option key={t.key} value={t.value} className="bg-jet">{t.code} · {t.short}</option>)}
            </select>
          </div>
          {data ? <LeaderboardTable rows={rows} filtered={(data.rows || []).length > 0} /> : <p className="text-white/40">Loading…</p>}
        </>
      )}
    </DashShell>
  );
}
