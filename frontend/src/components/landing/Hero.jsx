import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { ArrowRight, Lightbulb, Users, Code2, Rocket, MapPin } from "lucide-react";
import { Wordmark, LogoBars } from "@/components/Wordmark";
import { IMAGES } from "@/data/content";
import { usePublicConfig } from "@/context/PublicConfigContext";
import ajietLogo from "@/images/AJLOGOo.jpg.jpeg";

const up = (d) => ({ initial: { opacity: 0, y: 30, filter: "blur(10px)" }, animate: { opacity: 1, y: 0, filter: "blur(0px)" }, transition: { duration: 0.9, delay: d, ease: [0.22, 1, 0.36, 1] } });

export function useCountdown(target) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const i = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(i); }, []);
  const diff = Math.max(0, new Date(target).getTime() - now);
  return [Math.floor(diff / 864e5), Math.floor(diff / 36e5) % 24, Math.floor(diff / 6e4) % 60, Math.floor(diff / 1e3) % 60];
}

const Countdown = ({ target }) => {
  const vals = useCountdown(target || "2026-11-27T09:00:00+05:30");
  return (
    <div className="flex gap-4 sm:gap-6" data-testid="hero-countdown-timer">
      {["Days", "Hrs", "Min", "Sec"].map((l, i) => (
        <div key={l} className="text-center">
          <div className="font-display text-3xl font-bold tabular-nums text-white sm:text-4xl">{String(vals[i]).padStart(2, "0")}</div>
          <div className="font-mono text-[9px] uppercase tracking-[0.3em] text-white/40">{l}</div>
        </div>
      ))}
    </div>
  );
};

const PILLARS = [[Lightbulb, "Innovate"], [Users, "Collaborate"], [Code2, "Build"], [Rocket, "Create impact"]];

export default function Hero({ ready }) {
  const { timeline } = usePublicConfig();
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const sx = useSpring(mx, { stiffness: 60, damping: 20 });
  const sy = useSpring(my, { stiffness: 60, damping: 20 });
  const imgX = useTransform(sx, (v) => v * -18);
  const imgY = useTransform(sy, (v) => v * -12);
  const onMove = (e) => { mx.set(e.clientX / window.innerWidth - 0.5); my.set(e.clientY / window.innerHeight - 0.5); };
  const a = ready ? "animate" : "initial";

  return (
    <section onMouseMove={onMove} className="relative min-h-screen overflow-hidden pt-24 sm:pt-28" data-testid="hero-section">
      <div className="cyber-grid absolute inset-0 opacity-40" />
      <div className="absolute -left-40 top-20 h-[500px] w-[500px] rounded-full bg-cerulean/25 blur-[140px]" />
      <div className="absolute -right-20 bottom-0 h-[600px] w-[600px] rounded-full bg-neon/20 blur-[160px]" />

      <motion.div style={{ x: imgX, y: imgY }} className="pointer-events-none absolute inset-y-0 right-0 w-full md:w-[62%]"
        initial={{ opacity: 0, scale: 1.12 }} animate={ready ? { opacity: 1, scale: 1 } : {}} transition={{ duration: 1.8, ease: [0.22, 1, 0.36, 1] }}>
        <img src={IMAGES.heroGirl} alt="SANKALP neon cyborg muse" data-testid="hero-neon-girl-image"
          className="h-full w-full object-cover object-[60%_30%] opacity-60 md:opacity-100" />
        <div className="absolute inset-0 bg-gradient-to-r from-jet via-jet/40 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-jet via-transparent to-jet/40" />
      </motion.div>

      {[["8%", "#ff2d95", "55%", "0s"], ["18%", "#00c8ff", "40%", "1.2s"], ["30%", "#ff2d95", "28%", "2s"], ["4%", "#007ba7", "70%", "0.6s"]].map(([r, c, h, d], i) => (
        <span key={i} className="streak hidden md:block" style={{ right: r, top: "12%", height: h, background: `linear-gradient(${c}, transparent)`, boxShadow: `0 0 14px ${c}`, animationDelay: d }} />
      ))}

      <div className="relative z-10 mx-auto flex min-h-[calc(100vh-7rem)] max-w-7xl flex-col justify-center px-6 pb-16 sm:px-10">
        <motion.p {...up(0.1)} animate={ready ? up(0.1).animate : up(0.1).initial} className="mb-4 font-display text-xs uppercase text-white/80 spaced sm:mb-6 sm:text-sm">
          Ideas today<br />a brighter tomorrow
        </motion.p>

        <motion.h1 {...up(0.25)} animate={ready ? up(0.25).animate : up(0.25).initial} className="glitch">
          <Wordmark testid="hero-wordmark" className="glitch-run block text-[10vw] md:text-[11vw] lg:text-[8.5rem] xl:text-[10rem]" />
        </motion.h1>
        <motion.div {...up(0.4)} animate={ready ? up(0.4).animate : up(0.4).initial}><LogoBars className="mt-5 max-w-xl" /></motion.div>

        <motion.div {...up(0.5)} animate={ready ? up(0.5).animate : up(0.5).initial} className="mt-8">
          <p className="font-display text-base uppercase text-white/80 spaced md:text-lg">A national level</p>
          <p className="font-display text-xl font-bold uppercase spaced md:text-2xl"><span className="text-ice">24-Hour</span> <span className="text-neon">Hackathon</span> <span className="text-white/80 text-md ">(3rd Edition)</span></p>        </motion.div>

        <motion.div {...up(0.65)} animate={ready ? up(0.65).animate : up(0.65).initial} className="mt-8 flex flex-wrap gap-x-6 gap-y-3">
          {PILLARS.map(([Icon, t]) => (
            <span key={t} className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.2em] text-white/60"><Icon size={15} className="text-ice" />{t}</span>
          ))}
        </motion.div>

        <motion.div {...up(0.8)} animate={ready ? up(0.8).animate : up(0.8).initial} className="mt-8 flex flex-wrap items-center gap-3 sm:gap-4">
          <Link to="/auth?mode=register" className="btn-neon" data-testid="hero-register-cta">Register team <ArrowRight size={16} /></Link>
          <a href="#tracks" className="btn-ghost" data-testid="hero-explore-cta">Explore challenges</a>
        </motion.div>

        <motion.div {...up(1)} animate={ready ? up(1).animate : up(1).initial}
          className="glass glow-border mt-10 grid max-w-2xl grid-cols-1 gap-5 rounded-3xl p-5 sm:mt-12 sm:grid-cols-[auto_1px_1fr] sm:items-center sm:gap-6 sm:p-6">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-white/50">Prize pool</p>
            <p className="font-wordmark text-4xl font-black text-grad sm:text-5xl" data-testid="hero-prize-pool">₹75,000</p>
          </div>
          <div className="hidden h-full bg-white/10 sm:block" />
          <div>
            <p className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.3em] text-white/50">
              <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-neon" /> 27 & 28 Nov 2026 · T-minus
            </p>
            <Countdown target={timeline.hackathon_start} />
          </div>
        </motion.div>

        
<motion.div
  {...up(1.1)}
  animate={ready ? up(1.1).animate : up(1.1).initial}
  className="mt-6 flex flex-wrap items-center gap-4"
>
  {/* AJIET College Logo */}
  <div className="h-16 w-16 shrink-0 overflow-hidden rounded-full border border-white/20 bg-white shadow-[0_0_20px_rgba(0,200,255,0.15)]">
    <img
      src={ajietLogo}
      alt="AJIET College Logo"
      className="h-full w-full object-contain"
    />
  </div>

  {/* College Details */}
  <div className="flex flex-wrap items-center gap-4">
    <div className="flex flex-col gap-1">
      <p className="font-display text-sm font-semibold uppercase tracking-[0.18em] text-white/80">
        A J Institute of Engineering & Technology
      </p>

      <p className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-white/45">
        <MapPin size={13} className="text-neon" />
        Mangaluru, Karnataka
      </p>
    </div>
  </div>
</motion.div>

      </div>

      <div className="pointer-events-none absolute bottom-10 right-8 hidden text-right font-mono text-[10px] uppercase leading-5 tracking-[0.3em] text-white/40 lg:block" data-state={a}>
        <p>Subject // Sankalp</p><p>Status // <span className="text-neon">Awakening</span></p><p>12.91° N · 74.85° E</p>
      </div>
    </section>
  );
}
