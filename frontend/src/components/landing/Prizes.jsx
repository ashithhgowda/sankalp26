import { useEffect, useRef, useState } from "react";
import { useInView } from "framer-motion";
import { Crown, Medal, Award } from "lucide-react";
import { Reveal, SectionHead } from "@/components/Reveal";

const TIERS = [
  {
    icon: Medal,
    label: "TOP 2 TEAMS",
    description: "Compete for recognition and rewards",
    c: "#00c8ff",
  },
  {
    icon: Award,
    label: "EXCLUSIVE GOODIES",
    description: "Rewards for outstanding innovators",
    c: "#ff2d95",
  },
  {
    icon: Award,
    label: "EXPERT EVALUATION",
    description: "Industry and academic mentors",
    c: "#7aa7ff",
  },
];

const Counter = () => {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!inView) return;
    let raf; const t0 = performance.now();
    const step = (t) => { const p = Math.min(1, (t - t0) / 1800); setV(Math.round(75000 * (1 - Math.pow(1 - p, 3)))); if (p < 1) raf = requestAnimationFrame(step); };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [inView]);
  return <span ref={ref} data-testid="prize-pool-counter">₹{v.toLocaleString("en-IN")}</span>;
};

export default function Prizes() {
  return (
    <section id="prizes" className="relative overflow-hidden py-28" data-testid="prizes-section">
      <div className="absolute left-1/2 top-1/3 h-[500px] w-[800px] -translate-x-1/2 rounded-full bg-neon/15 blur-[160px]" />
      <div className="relative mx-auto max-w-7xl px-6 sm:px-10">
        <SectionHead eyebrow="Rewards" title="Built to win." accent="Built to matter." testid="prizes-heading" />
        <Reveal>
          <div className="glass glow-border relative mx-auto max-w-4xl overflow-hidden rounded-[2rem] px-8 py-14 text-center">
            <div className="scanline" />
            <p className="font-display text-sm uppercase text-white/70 spaced">Total prize pool</p>
            <p className="mt-4 font-wordmark text-5xl font-black text-grad sm:text-7xl lg:text-8xl"><Counter /></p>
            <p className="mx-auto mt-5 max-w-md text-sm text-white/50">Distributed across the top teams, judged by mentors from industry and academia.</p>
          </div>
        </Reveal>
        <div className="mx-auto mt-6 grid max-w-4xl grid-cols-1 gap-4 md:grid-cols-3">
          {TIERS.map((t, i) => (
            <Reveal key={t.label} delay={i * 0.1} className={t.h}>
              <div data-testid={`prize-tier-${i + 1}`} className="glass glow-border card-scan rounded-3xl p-7 text-center transition-transform duration-500 hover:-translate-y-1.5">
                <t.icon size={30} style={{ color: t.c, filter: `drop-shadow(0 0 12px ${t.c})` }} className="mx-auto" />
                <p className="mt-5 font-display text-lg font-bold uppercase tracking-[0.15em]" style={{ color: t.c }}>
  {t.label}
</p>
<p className="mt-3 text-sm text-white/60">
  {t.description}
</p>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}