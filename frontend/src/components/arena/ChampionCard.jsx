import { motion } from "framer-motion";
import { Crown } from "lucide-react";

export default function ChampionCard({ champion, prize, announcement }) {
  return (
    <motion.div initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8 }}
      className="glass-strong glow-border relative mb-8 overflow-hidden rounded-[2rem] p-8 sm:p-10" data-testid="arena-champion-card">
      <div className="absolute -right-10 -top-10 h-64 w-64 rounded-full bg-[#ffcf5a]/20 blur-[90px]" />
      <div className="relative flex flex-wrap items-center gap-8">
        <motion.div animate={{ rotate: [0, -6, 6, 0], y: [0, -6, 0] }} transition={{ duration: 3, repeat: Infinity }}
          className="flex h-24 w-24 items-center justify-center rounded-3xl border border-[#ffcf5a]/60 bg-[#ffcf5a]/10 shadow-[0_0_60px_-10px_#ffcf5a]">
          <Crown size={44} className="text-[#ffcf5a]" />
        </motion.div>
        <div className="min-w-0 flex-1">
          <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#ffcf5a]">Arena champion</p>
          <p className="mt-2 font-wordmark text-3xl font-black text-white sm:text-4xl" data-testid="arena-champion-name">{champion.name}</p>
          {champion.team_name && <p className="text-sm text-white/55">Team {champion.team_name}</p>}
          <p className="mt-3 font-mono text-xs text-white/60"><span className="text-ice">{champion.xp} XP</span> · {champion.completed} challenges completed</p>
        </div>
      </div>
      <p className="relative mt-6 text-base text-white/80">
        Congratulations, {champion.name}! {prize ? <>You've won <span className="text-neon">{prize}</span>.</> : "Your prize will be announced by the organisers."}
      </p>
      {announcement && <p className="relative mt-2 text-sm text-white/55">{announcement}</p>}
    </motion.div>
  );
}
