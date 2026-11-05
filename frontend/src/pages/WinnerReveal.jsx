import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Crown, Maximize2, Medal } from "lucide-react";
import { Wordmark, LogoBars } from "@/components/Wordmark";
import { api } from "@/lib/api";
import { beep, burst, sideCannons } from "@/lib/arenaFx";
import { IMAGES } from "@/data/content";

const TIERS = {
  2: ["Runner-up", "#00C8FF", Medal],
  1: ["Champion", "#FF2D95", Crown],
};

const STEPS = ["idle", "count", "r2", "drum", "r1"];

function Count({ from, onDone }) {
  const [n, setN] = useState(from);

  useEffect(() => {
    if (n === 0) {
      onDone();
      return;
    }

    beep("tick");
    const t = setTimeout(() => setN(n - 1), 1000);
    return () => clearTimeout(t);
  }, [n, onDone]);

  return (
    <AnimatePresence mode="wait">
      {n > 0 && (
        <motion.div
          key={n}
          initial={{
            scale: 2.4,
            opacity: 0,
            filter: "blur(20px)",
          }}
          animate={{
            scale: 1,
            opacity: 1,
            filter: "blur(0px)",
          }}
          exit={{ scale: 0.4, opacity: 0 }}
          transition={{ duration: 0.5 }}
          className="relative font-wordmark text-[38vw] font-black leading-none sm:text-[22rem]"
          data-testid="reveal-countdown-number"
        >
          <span className={n % 2 ? "wm-sankalp" : "wm-26"}>
            {n}
          </span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function WinnerCard({ row, rank, big }) {
  const [label, color, Icon] = TIERS[rank];
  const members = row?.members || [];

  return (
    <motion.div
      initial={{
        opacity: 0,
        y: 80,
        scale: 0.8,
        rotateX: 40,
      }}
      animate={{
        opacity: 1,
        y: 0,
        scale: 1,
        rotateX: 0,
      }}
      transition={{
        type: "spring",
        stiffness: 90,
        damping: 14,
      }}
      data-testid={`reveal-winner-${rank}`}
      className={`glass-strong relative overflow-hidden rounded-[2rem] text-center ${
        big ? "p-10 sm:p-14" : "p-7"
      }`}
      style={{
        border: `1px solid ${color}88`,
        boxShadow: `0 0 120px -30px ${color}`,
      }}
    >
      <div className="scanline" />

      <Icon
        size={big ? 64 : 40}
        className="mx-auto"
        style={{
          color,
          filter: `drop-shadow(0 0 20px ${color})`,
        }}
      />

      <p
        className="mt-4 font-mono text-xs uppercase tracking-[0.4em]"
        style={{ color }}
      >
        {label}
      </p>

      <p
        className={`mt-5 font-wordmark font-black text-white break-words ${
          big ? "text-3xl sm:text-5xl" : "text-2xl"
        }`}
      >
        {row?.team_name || "TEAM NAME"}
      </p>

      {row?.title && (
        <p className="mt-4 text-sm text-white/60">
          {row.title}
        </p>
      )}

      {members.length > 0 && (
        <p className="mt-5 font-mono text-xs leading-6 text-white/50">
          {members
            .map((member) =>
              typeof member === "string"
                ? member
                : member.full_name || member.name
            )
            .filter(Boolean)
            .join(" · ")}
        </p>
      )}
    </motion.div>
  );
}

export default function WinnerReveal() {
  const [rows, setRows] = useState(null);
  const [step, setStep] = useState(0);

  useEffect(() => {
    api
      .get("/leaderboard")
      .then((r) =>
        setRows(r.data.rows.filter((x) => x.judges > 0))
      );
  }, []);

  const s = STEPS[step];

  const next = useCallback(
    () => setStep((x) => Math.min(x + 1, STEPS.length - 1)),
    []
  );

  useEffect(() => {
    if (s === "r2") {
      beep("good");
      burst(false);
    }

    if (s === "r1") {
      beep("win");
      sideCannons();
      setTimeout(() => burst(true), 600);
    }
  }, [s]);

  useEffect(() => {
    const k = (e) => {
      if (
        [" ", "ArrowRight", "Enter"].includes(e.key) &&
        !["count", "drum"].includes(s)
      ) {
        e.preventDefault();
        next();
      }
    };

    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [s, next]);

  const at = (r) =>
    rows?.find((x) => x.rank === r) || rows?.[r - 1];

  return (
    <div
      className="grain relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-jet px-6 py-20"
      data-testid="winner-reveal-page"
    >
      <div className="cyber-grid absolute inset-0 opacity-40" />

      <img
        src={IMAGES.heroGirl}
        alt=""
        className="pointer-events-none absolute inset-y-0 right-0 h-full w-1/2 object-cover opacity-20"
      />

      <div className="absolute inset-0 bg-gradient-to-r from-jet via-jet/80 to-jet/40" />

      <div className="absolute left-6 top-6 z-10 flex gap-4">
        <Link
          to="/admin"
          className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-white/40 hover:text-white"
          data-testid="reveal-back-link"
        >
          <ArrowLeft size={14} /> Admin
        </Link>

        <button
          onClick={() => document.documentElement.requestFullscreen?.()}
          className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.25em] text-white/40 hover:text-white"
          data-testid="reveal-fullscreen"
        >
          <Maximize2 size={14} /> Fullscreen
        </button>
      </div>

      <div className="relative z-10 flex w-full max-w-6xl flex-col items-center">
        {s === "idle" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-center"
          >
            <p className="font-display text-sm uppercase text-white/70 spaced">
              Closing ceremony
            </p>

            <Wordmark
              className="mt-6 block text-[14vw] sm:text-[9rem]"
              testid="reveal-wordmark"
            />

            <LogoBars className="mx-auto mt-5 max-w-xl" />

            <p className="mt-6 font-display text-xl uppercase text-white/80 spaced">
              The winners are…
            </p>

            {rows && rows.length === 0 && (
              <p
                className="mt-6 text-sm text-neon"
                data-testid="reveal-no-results"
              >
                No scored submissions yet — scores are needed before the reveal.
              </p>
            )}

            <button
              onClick={next}
              disabled={!rows?.length}
              className="btn-neon mt-10 disabled:opacity-40"
              data-testid="reveal-start-button"
            >
              Begin the reveal
            </button>

            <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.3em] text-white/35">
              Space / → to advance
            </p>
          </motion.div>
        )}

        {s === "count" && <Count from={10} onDone={next} />}

        {s === "drum" && (
          <>
            <p className="mb-4 font-display text-lg uppercase text-neon spaced">
              And the champion is
            </p>
            <Count from={3} onDone={next} />
          </>
        )}

        {/* Winner reveal — heading intentionally removed */}
        {["r2", "r1"].includes(s) && (
          <div className="w-full">
            {s === "r1" && (
              <div className="mx-auto mb-6 max-w-3xl">
                <WinnerCard row={at(1)} rank={1} big />
              </div>
            )}

            <div className="mx-auto flex max-w-4xl justify-center">
              <WinnerCard
                row={at(2)}
                rank={2}
                big={s === "r2"}
              />
            </div>

            {s !== "r1" ? (
              <button
                onClick={next}
                className="btn-ghost mx-auto mt-10 flex"
                data-testid="reveal-next-button"
              >
                Reveal the champion
              </button>
            ) : (
              <p className="mt-10 text-center font-display text-xl uppercase text-white/80 spaced">
                Build. Breakthrough.{" "}
                <span className="text-neon">Belong.</span>
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}