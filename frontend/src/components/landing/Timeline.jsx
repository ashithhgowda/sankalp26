import { usePublicConfig } from "@/context/PublicConfigContext";
import { Reveal, SectionHead } from "@/components/Reveal";

const ITEMS = [
  ["abstract_deadline", "Abstract submission closes", "Submit a one-page PDF for one of six topics"],
  ["selection_announcement", "Selection announcement", "Selected teams continue to organizer-configured payment"],
  ["payment_deadline", "Payment deadline", "Verified payment is followed by explicit registration approval"],
  ["hackathon_start", "SANKALP'26 goes live", "24 hours of building at AJIET, Mangaluru"],
];

const statusOf = (items, index) => {
  const now = Date.now();
  const current = new Date(items[index].date).getTime();
  if (now > current) return "done";
  if (index === 0 || now > new Date(items[index - 1].date).getTime()) return "live";
  return "next";
};

export default function Timeline() {
  const { timeline } = usePublicConfig();
  const items = ITEMS.filter(([key]) => timeline[key]).map(([key, title, sub], index) => ({ key, title, sub, date: timeline[key], n: String(index + 1).padStart(2, "0") }));
  return <section id="timeline" className="relative py-28" data-testid="timeline-section"><div className="mx-auto max-w-7xl px-6 sm:px-10">
    <SectionHead eyebrow="Key milestones" title="The countdown" accent="to ignition." testid="timeline-heading" sub="Core deadlines are controlled by the organizers and shown in India Standard Time." />
    <div className="relative grid grid-cols-1 gap-4 md:grid-cols-4">
      <div className="absolute left-0 right-0 top-[46px] hidden h-px bg-gradient-to-r from-ice via-white/20 to-neon md:block" />
      {items.map((item, index) => { const status = statusOf(items, index); const date = new Date(item.date); return <Reveal key={item.key} delay={index * 0.12}><div data-testid={`timeline-phase-${item.n}`} className="relative">
        <div className="mb-8 flex items-center gap-3"><span className={`relative z-10 h-[18px] w-[18px] rounded-full border ${status === "live" ? "border-neon bg-neon pulse-dot" : status === "done" ? "border-ice bg-ice" : "border-white/30 bg-jet"}`} /><span className={`font-mono text-[10px] uppercase tracking-[0.3em] ${status === "live" ? "text-neon" : "text-white/40"}`}>{status === "live" ? "Current window" : status === "done" ? "Completed" : "Upcoming"}</span></div>
        <article className="glass glow-border card-scan rounded-3xl p-7"><p className="font-mono text-[10px] tracking-[0.3em] text-white/40">PHASE {item.n}</p><p className="mt-3 font-wordmark text-xl font-black text-white">{date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", timeZone: "Asia/Kolkata" }).toUpperCase()}</p><p className="mt-1 font-mono text-[10px] tracking-[0.2em] text-ice">{date.toLocaleString("en-IN", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Kolkata", timeZoneName: "short" })}</p><h3 className="mt-6 font-display text-xl font-bold uppercase text-white">{item.title}</h3><p className="mt-2 text-sm text-white/55">{item.sub}</p></article>
      </div></Reveal>; })}
    </div>
  </div></section>;
}