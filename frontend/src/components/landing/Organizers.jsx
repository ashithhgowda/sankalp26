import { HOSTS, SPONSORS, TEAM } from "@/data/content";
import { Reveal, SectionHead } from "@/components/Reveal";

const TICKER = ["AJIET", "IEEE", "Innovation", "ECE", "Sustainability", "Smart Tech", "Build", "Breakthrough", "Belong"];

export default function Organizers() {
  return (
    <section id="team" className="relative py-28" data-testid="organizers-section">
      <div className="mb-20 overflow-hidden border-y border-white/10 py-6">
        <div className="marquee flex w-max gap-12">
          {[...TICKER, ...TICKER, ...TICKER, ...TICKER].map((t, i) => (
            <span key={i} className={`font-wordmark text-3xl font-black uppercase sm:text-5xl ${i % 2 ? "text-white/10" : "text-transparent [-webkit-text-stroke:1px_rgba(255,45,149,0.6)]"}`}>{t}</span>
          ))}
        </div>
      </div>
      <div className="mx-auto max-w-7xl px-6 sm:px-10">
        <SectionHead eyebrow="Event ecosystem" title="Where ideas meet" accent="execution & mentorship." testid="organizers-heading" />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {HOSTS.map((h, i) => (
            <Reveal key={h.name} delay={i * 0.08}>
              <div className="glass h-full rounded-3xl p-6" data-testid={`host-card-${i}`}>
                <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-ice">{h.role}</p>
                <p className="mt-4 font-display text-lg font-bold uppercase leading-snug tracking-wide text-white">{h.name}</p>
              </div>
            </Reveal>
          ))}
        </div>

        <p className="eyebrow mb-6 mt-16">Our sponsors</p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {SPONSORS.map((s, i) => (
            <Reveal key={s.name} delay={i * 0.1}>
              <div data-testid={`sponsor-card-${i}`} className="glass glow-border card-scan flex items-center gap-6 rounded-[1.75rem] p-8 transition-transform duration-500 hover:-translate-y-1">
                <span className="h-14 w-14 shrink-0 rounded-full" style={{ background: `radial-gradient(circle at 30% 30%, #fff, ${s.color} 45%, #0a0a0a)`, boxShadow: `0 0 30px ${s.color}80` }} />
                <div>
                  <p className="font-editorial text-2xl font-extrabold uppercase tracking-wide text-white sm:text-3xl">{s.name}</p>
                  <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-white/50">{s.sub}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>

        <p className="eyebrow mb-6 mt-20">Organising team · the people behind Sankalp'26</p>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {TEAM.map((g, i) => (
            <Reveal key={g.group} delay={(i % 3) * 0.08}>
              <div className="glass h-full rounded-3xl p-7" data-testid={`team-group-${i}`}>
                <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-neon">{g.group}</p>
                <ul className="mt-5 space-y-4">
                  {g.people.map(([n, r]) => (
                    <li key={n}>
                      <p className="font-display text-base font-bold uppercase tracking-wide text-white">{n}</p>
                      {r.startsWith("+91") ? <a href={`tel:${r.replace(/\s/g, "")}`} className="text-sm text-ice hover:underline">{r}</a> : <p className="text-sm text-white/50">{r}</p>}
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
