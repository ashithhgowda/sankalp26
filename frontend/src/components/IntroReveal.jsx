import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const BOOT = ["> INIT sankalp.sys", "> LINK ieee.ajiet.node ........ OK", "> LOAD neural_core v26 ......... OK", "> RESOLVE // संकल्प"];
const LETTERS = "SANKALP".split("");
const EASE = [0.76, 0, 0.24, 1];

export default function IntroReveal({ onDone }) {
  const [leaving, setLeaving] = useState(false);
  const [pct, setPct] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => setLeaving(true), 2600);
    const t2 = setTimeout(onDone, 3300);
    const iv = setInterval(() => setPct((p) => Math.min(100, p + 4)), 95);
    return () => { clearTimeout(t1); clearTimeout(t2); clearInterval(iv); };
  }, [onDone]);

  return (
    <div className="fixed inset-0 z-[100] overflow-hidden" data-testid="intro-reveal">
      <motion.div className="absolute inset-x-0 top-0 h-1/2 bg-[#050505]" animate={{ y: leaving ? "-100%" : 0 }} transition={{ duration: 0.8, ease: EASE }} />
      <motion.div className="absolute inset-x-0 bottom-0 h-1/2 bg-[#050505]" animate={{ y: leaving ? "100%" : 0 }} transition={{ duration: 0.8, ease: EASE }} />

      <motion.div
        className="absolute inset-0 flex flex-col items-center justify-center px-6"
        animate={leaving ? { opacity: 0, scale: 1.12, filter: "blur(14px)" } : {}}
        transition={{ duration: 0.55 }}
      >
        <div className="cyber-grid absolute inset-0 opacity-70" />
        <div className="scanline" />
        <motion.div className="absolute left-1/2 top-1/2 h-px w-[80vw] -translate-x-1/2 bg-gradient-to-r from-transparent via-ice to-transparent"
          initial={{ scaleX: 0, opacity: 0 }} animate={{ scaleX: [0, 1, 1], opacity: [0, 1, 0] }} transition={{ duration: 1.1, delay: 0.5 }} />

        <div className="absolute left-6 top-6 space-y-1 font-mono text-[10px] text-ice/70 sm:left-10 sm:top-10 sm:text-xs">
          {BOOT.map((l, i) => (
            <motion.p key={l} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 + i * 0.18 }}>{l}</motion.p>
          ))}
        </div>

        <div className="relative font-wordmark text-[13vw] font-black leading-none tracking-[-0.02em] sm:text-[10vw]">
          {LETTERS.map((c, i) => (
            <motion.span key={i} className="wm-sankalp inline-block"
              initial={{ opacity: 0, y: 60, filter: "blur(24px)", scaleY: 1.6 }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)", scaleY: 1 }}
              transition={{ delay: 0.9 + i * 0.07, duration: 0.6, ease: [0.22, 1, 0.36, 1] }}>{c}</motion.span>
          ))}
          <motion.span className="wm-26 inline-block"
            initial={{ opacity: 0, scale: 2.4, x: 40 }}
            animate={{ opacity: [0, 1, 0.4, 1], scale: 1, x: 0 }}
            transition={{ delay: 1.55, duration: 0.55 }}>'26</motion.span>
          <motion.div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent mix-blend-overlay"
            initial={{ x: "-120%" }} animate={{ x: "120%" }} transition={{ delay: 1.9, duration: 0.7 }} />
        </div>

        <div className="mt-6 flex w-[min(80vw,720px)] items-center gap-1.5">
          <motion.span className="h-[5px] w-12 -skew-x-[30deg] bg-ice shadow-[0_0_14px_#00c8ff]" initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: 1.7, duration: 0.3 }} style={{ originX: 0 }} />
          <motion.span className="h-[5px] w-20 -skew-x-[30deg] bg-neon shadow-[0_0_14px_#ff2d95]" initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: 1.8, duration: 0.3 }} style={{ originX: 0 }} />
          <motion.span className="h-px flex-1 bg-white/40" initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ delay: 1.9, duration: 0.5 }} style={{ originX: 0 }} />
        </div>

        <motion.p className="mt-6 text-center font-display text-xs uppercase text-white/70 spaced sm:text-sm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 2.0 }}>
          Ideas today · <span className="text-neon">A brighter tomorrow</span>
        </motion.p>

        <div className="absolute bottom-10 left-1/2 w-[min(70vw,420px)] -translate-x-1/2">
          <div className="mb-2 flex justify-between font-mono text-[10px] text-white/50">
            <span>BOOTING EXPERIENCE</span><span data-testid="intro-progress">{pct}%</span>
          </div>
          <div className="h-px w-full bg-white/10">
            <div className="h-px bg-gradient-to-r from-ice to-neon" style={{ width: `${pct}%` }} />
          </div>
        </div>

        <button data-testid="intro-skip-button" onClick={onDone}
          className="absolute right-6 top-6 font-mono sm:top-10 text-[10px] uppercase tracking-[0.3em] text-white/40 transition-colors hover:text-white sm:right-10">
          Skip →
        </button>
      </motion.div>
    </div>
  );
}
