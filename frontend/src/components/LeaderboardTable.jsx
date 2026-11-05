import { Crown } from "lucide-react";

const MEDAL = { 1: "#FF2D95", 2: "#00C8FF", 3: "#7AA7FF" };

export default function LeaderboardTable({ rows, filtered = false }) {
  if (!rows.length) return <p className="glass rounded-3xl p-10 text-center text-white/50" data-testid="leaderboard-empty">{filtered ? "No teams match your search or filter." : "No submissions yet. The grid is warming up."}</p>;
  return (
    <div className="glass overflow-x-auto rounded-3xl" data-testid="leaderboard-table">
      <table className="w-full min-w-[760px] text-left text-sm">
        <thead>
          <tr className="border-b border-white/10 font-mono text-[10px] uppercase tracking-[0.25em] text-white/40">
            <th className="px-6 py-4">Rank</th><th className="px-4 py-4">Team / Project</th><th className="px-4 py-4">Innov.</th>
            <th className="px-4 py-4">Tech</th><th className="px-4 py-4">Feas.</th><th className="px-4 py-4">Pres.</th><th className="px-4 py-4">Judges</th><th className="px-6 py-4 text-right">Score /40</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.submission_id} data-testid={`leaderboard-rank-row-${r.rank}`} className="border-b border-white/5 transition-colors hover:bg-white/[0.03]">
              <td className="px-6 py-4">
                <span className="flex items-center gap-2 font-wordmark text-xl font-black" style={{ color: MEDAL[r.rank] || "rgba(255,255,255,.6)" }}>
                  {r.rank <= 3 && <Crown size={14} />}{String(r.rank).padStart(2, "0")}
                </span>
              </td>
              <td className="px-4 py-4">
                <p className="font-display text-base font-bold uppercase tracking-wide text-white">{r.team_name}</p>
                <p className="text-xs text-white/45">{r.title} · {r.category}</p>
              </td>
              {["innovation", "technical", "feasibility", "presentation"].map((c) => <td key={c} className="px-4 py-4 font-mono text-white/70">{r[c]}</td>)}
              <td className="px-4 py-4 font-mono text-white/50">{r.judges}</td>
              <td className="px-6 py-4 text-right font-wordmark text-xl font-black text-grad" data-testid={`leaderboard-score-${r.rank}`}>{r.score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
