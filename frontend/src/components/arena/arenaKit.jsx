import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink } from "react-router-dom";
import { animate } from "framer-motion";
import { Brain, Bug, Crown, Droplet, Eye, Hexagon, Sparkles, Timer, Volume2, VolumeX, Zap, Puzzle, Cpu, Code2, Terminal, HelpCircle } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { isMuted, setMuted } from "@/lib/arenaFx";

export const BADGE_ICONS = { first_blood: Droplet, logic_master: Brain, debugging_ninja: Bug, quiz_crusher: Zap, output_oracle: Eye,
  trivia_titan: Sparkles, lightning: Timer, polymath: Hexagon, arena_champion: Crown };
export const CAT_ICONS = { 
  logic: Puzzle,
  kenken: Puzzle,
  aptitude: Cpu,
  sudoku: Puzzle,
  quiz: Cpu,
  debug: Bug,
  predict: Terminal,
  trivia: HelpCircle,
  rapid: Timer,
  code: Code2,
 };
export const DIFF_STYLE = { easy: "border-ice/40 text-ice", medium: "border-[#7aa7ff]/50 text-[#9fbcff]", hard: "border-neon/50 text-neon" };
export const PLAYER_ROLES = ["team", "member"];

export function useArena() {
  const { user } = useAuth();
  const [state, setState] = useState(null);
  const [me, setMe] = useState(null);
  const isPlayer = !!user && PLAYER_ROLES.includes(user.role);
  const reload = useCallback(async () => {
    const [s, m] = await Promise.all([api.get("/arena/state"), isPlayer ? api.get("/arena/me") : Promise.resolve(null)]);
    setState(s.data);
    setMe(m ? m.data : null);
  }, [isPlayer]);
  useEffect(() => { reload().catch(() => {}); }, [reload]);
  return { state, me, reload, isPlayer, user };
}

export function AnimatedNumber({ value, className = "", testid }) {
  const [v, setV] = useState(0);
  const prev = useRef(0);
  useEffect(() => {
    const c = animate(prev.current, value || 0, { duration: 1.2, ease: "easeOut", onUpdate: (x) => setV(Math.round(x)) });
    prev.current = value || 0;
    return () => c.stop();
  }, [value]);
  return <span className={className} data-testid={testid}>{v.toLocaleString("en-IN")}</span>;
}

export function BadgeChip({ badge, earned, size = "md" }) {
  const Icon = BADGE_ICONS[badge.key] || Sparkles;
  if (size === "sm") return <span title={badge.name} className="inline-flex h-6 w-6 items-center justify-center rounded-full border border-neon/40 bg-neon/10 text-neon"><Icon size={12} /></span>;
  return (
    <div data-testid={`badge-${badge.key}`} className={`rounded-2xl border p-4 transition-colors ${earned ? "border-neon/50 bg-neon/10 shadow-[0_0_24px_-10px_#ff2d95]" : "border-white/10 bg-white/[0.02] opacity-50"}`}>
      <Icon size={20} className={earned ? "text-neon" : "text-white/40"} />
      <p className="mt-3 font-display text-sm font-bold uppercase tracking-wide text-white">{badge.name}</p>
      <p className="text-[11px] leading-snug text-white/45">{badge.desc}</p>
      {badge.xp > 0 && <p className="mt-2 font-mono text-[10px] text-ice">+{badge.xp} XP</p>}
    </div>
  );
}

function SoundToggle() {
  const [muted, set] = useState(isMuted());
  return (
    <button onClick={() => { setMuted(!muted); set(!muted); }} data-testid="arena-sound-toggle" aria-label={muted ? "Turn sound on" : "Mute sound"}
      className="flex items-center gap-2 rounded-full border border-white/10 px-4 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-white/60 transition-colors hover:text-white">
      {muted ? <VolumeX size={14} /> : <Volume2 size={14} className="text-ice" />} {muted ? "Sound off" : "Sound on"}
    </button>
  );
}

export function ArenaNav() {
  const links = [["/arena", "Dashboard"], ["/arena/play", "Play"], ["/arena/leaderboard", "XP leaderboard"]];
  return (
    <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
      <div className="glass flex flex-wrap gap-1 rounded-full p-1">
        {links.map(([to, l]) => (
          <NavLink key={to} to={to} end data-testid={`arena-nav-${l.split(" ")[0].toLowerCase()}`}
            className={({ isActive }) => `rounded-full px-5 py-2.5 font-mono text-[10px] uppercase tracking-[0.22em] transition-colors ${isActive ? "bg-gradient-to-r from-cerulean to-neon text-white" : "text-white/55 hover:text-white"}`}>{l}</NavLink>
        ))}
      </div>
      <SoundToggle />
    </div>
  );
}

export const STATUS_COPY = {
  live: ["Live", "Scoring is open — every correct first answer earns XP."],
  upcoming: ["Opening soon", "Practice freely. XP starts counting when the Arena opens."],
  closed: ["Closed", "Scoring is frozen. Final standings are being verified."],
  final: ["Final", "Results are final. Congratulations to every player."],
};

export function StatusPill({ status }) {
  const live = status === "live";
  return (
    <span data-testid="arena-status-pill" className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.25em] ${live ? "border-neon/60 text-neon" : "border-white/20 text-white/60"}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${live ? "pulse-dot bg-neon" : "bg-white/40"}`} />{STATUS_COPY[status]?.[0] || status}
    </span>
  );
}
