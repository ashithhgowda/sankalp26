import * as Icons from "lucide-react";
import { Reveal, SectionHead } from "@/components/Reveal";
import { usePublicConfig } from "@/context/PublicConfigContext";

const ICONS = { drone: "Crosshair", food: "Leaf", v2v: "Car", stethoscope: "HeartPulse", sanitation: "Recycle", water: "Droplets" };

export default function Tracks() {
  const { topics } = usePublicConfig();
  return (
    <section id="tracks" className="relative py-28" data-testid="tracks-section">
      <div className="absolute right-0 top-40 h-96 w-96 rounded-full bg-cerulean/20 blur-[140px]" />
      <div className="relative mx-auto max-w-7xl px-6 sm:px-10">
        <SectionHead eyebrow="Problem statements // 06" title="Real-world challenges." accent="Room to build boldly." testid="tracks-heading"
          sub="Pick one. Find the sharpest problem inside it. Prototype the answer in 24 hours." />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {topics.map((t, i) => {
            const Icon = Icons[ICONS[t.topic_id]] || Icons.Cpu;
            const big = [0, 3, 4].includes(i);
            const code = String(i + 1).padStart(2, "0");
            return (
              <Reveal key={t.topic_id} delay={(i % 3) * 0.08} className={big ? "lg:col-span-2" : ""}>
                <article data-testid={`track-card-${t.topic_id}`}
                  className="glass glow-border card-scan group relative flex h-full min-h-[280px] flex-col justify-between overflow-hidden rounded-[1.75rem] p-8 transition-transform duration-500 hover:-translate-y-1.5">
                  <span className="pointer-events-none absolute -right-4 -top-8 font-wordmark text-[9rem] font-black leading-none text-white/[0.03] transition-colors duration-500 group-hover:text-neon/10">{code}</span>
                  <div className="flex items-center justify-between">
                    <span className="flex h-12 w-12 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-ice transition-colors duration-500 group-hover:border-neon/50 group-hover:text-neon">
                      <Icon size={22} />
                    </span>
                    <span className="rounded-full border border-white/10 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.25em] text-white/50">{code} · {t.short}</span>
                  </div>
                  <div className="mt-10">
                    <h3 className={`font-display font-bold uppercase leading-tight tracking-wide text-white ${big ? "text-2xl sm:text-3xl" : "text-xl"}`}>{t.title}</h3>
                    <p className="mt-3 max-w-xl text-sm leading-relaxed text-white/55">{t.description}</p>
                  </div>
                </article>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
