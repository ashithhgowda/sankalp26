import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Bug, Cpu, HelpCircle, Puzzle, Terminal, Timer } from "lucide-react";
import { Reveal, SectionHead } from "@/components/Reveal";
import { api } from "@/lib/api";

const MODES = [[Puzzle, "Logic puzzles"], [Cpu, "Technical quiz"], [Bug, "Debug the code"], [Terminal, "Predict the output"], [Timer, "Rapid fire"], [HelpCircle, "Hackathon trivia"]];

export default function ArenaTeaser() {
  const [top, setTop] = useState([]);
  useEffect(() => { api.get("/arena/leaderboard").then((r) => setTop(r.data.rows.slice(0, 3))).catch(() => {}); }, []);
  return (
    <section id="arena" className="relative py-28" data-testid="arena-teaser-section">
      <div className="absolute left-0 top-20 h-96 w-96 rounded-full bg-neon/15 blur-[140px]" />
      <div className="relative mx-auto max-w-7xl px-6 sm:px-10">
        <SectionHead eyebrow="Arena // games & XP" title="ARENA —" accent="Play. Solve. Dominate." testid="arena-teaser-heading"
          sub="Take a break. Challenge your brain. Climb the leaderboard. Every registered participant gets an individual XP profile." />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.4fr_1fr]">
          <Reveal>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {MODES.map(([Icon, l]) => (
                <div key={l} className="glass glow-border card-scan rounded-3xl p-6 transition-transform duration-500 hover:-translate-y-1">
                  <Icon size={22} className="text-ice" />
                  <p className="mt-5 font-display text-base font-bold uppercase tracking-wide text-white">{l}</p>
                </div>
              ))}
            </div>
          </Reveal>
          <Reveal delay={0.1}>
            <div className="glass-strong glow-border flex h-full flex-col rounded-[2rem] p-8">
              <p className="eyebrow mb-4">Live XP leaders</p>
              {top.length ? top.map((r) => (
                <div key={r.user_id} className="flex items-center justify-between border-b border-white/5 py-3">
                  <span className="text-white"><span className="mr-3 font-wordmark text-sm font-black text-neon">{r.rank}</span>{r.name}</span>
                  <span className="font-mono text-sm text-ice">{r.xp} XP</span>
                </div>
              )) : <p className="text-sm text-white/45">The board is empty. Your name could be first.</p>}
              <Link to="/arena" className="btn-neon mt-auto self-start" style={{ marginTop: "2rem" }} data-testid="arena-teaser-cta">Enter the Arena <ArrowRight size={16} /></Link>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
