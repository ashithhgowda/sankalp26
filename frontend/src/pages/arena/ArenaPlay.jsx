
import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Play,
  Timer,
  Puzzle,
  CheckCircle2,
} from "lucide-react";

import DashShell from "@/components/DashShell";
import QuestionPlayer from "@/components/arena/QuestionPlayer";
import RapidPlayer from "@/components/arena/RapidPlayer";
import PuzzlePlayer from "@/components/arena/PuzzlePlayer";

import {
  ArenaNav,
  CAT_ICONS,
  StatusPill,
  useArena,
} from "@/components/arena/arenaKit";

import { ArenaTitle } from "@/pages/arena/ArenaHome";
import { api } from "@/lib/api";

const PUZZLE_GAMES = ["sudoku", "kenken"];

function getCategoryIcon(category) {
  return CAT_ICONS?.[category] || Puzzle;
}

function CategoryCard({ category, onPlay }) {
  const Icon = getCategoryIcon(category.key);
  const isPuzzle = PUZZLE_GAMES.includes(category.key);
  const disabled = category.enabled === false;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass glow-border card-scan flex flex-col rounded-3xl p-5 transition-transform duration-300 hover:-translate-y-1 sm:p-6"
      data-testid={`arena-category-${category.key}`}
    >
      <div className="flex items-center justify-between gap-2">
        <Icon size={23} className="text-ice" />

        <span className="font-mono text-[9px] uppercase tracking-[0.18em] text-white/40">
          {disabled ? "Disabled" : isPuzzle ? "Puzzle mode" : category.count > 0 ? "Challenge mode" : "Coming soon"}
        </span>
      </div>

      <p className="mt-5 min-h-12 font-display text-base font-bold uppercase tracking-wide text-white sm:text-lg">
        {category.name}
      </p>

      <button
        onClick={onPlay}
        disabled={disabled}
        className="btn-ghost mt-5 !py-3 !text-[10px] disabled:cursor-not-allowed disabled:opacity-40"
        data-testid={`arena-play-category-${category.key}`}
      >
        <Play size={13} />
        {disabled ? "Disabled" : isPuzzle ? "Play puzzle" : "Play"}
      </button>
    </motion.div>
  );
}

export default function ArenaPlay() {
  const { state, me, reload, isPlayer } = useArena();
  const nav = useNavigate();

  const [session, setSession] = useState(null);
  const [rapid, setRapid] = useState(null);
  const [puzzleGame, setPuzzleGame] = useState(null);
  const [notice, setNotice] = useState("");

  const refresh = useCallback(() => {
    reload();
  }, [reload]);

  const gate = (callback) => {
    if (isPlayer) {
      callback();
    } else {
      nav("/auth?mode=login");
    }
  };

  // ------------------------------------------------------
  // GAME CATEGORY LAUNCHER
  // ------------------------------------------------------

  function playCategory(category) {
    gate(() => {
      setNotice("");
      setSession(null);
      setRapid(null);

      // Sudoku and KenKen have their own puzzle interface.
      if (PUZZLE_GAMES.includes(category.key)) {
        setPuzzleGame(category.key);
        return;
      }

      // Don't open an empty question session.
      if (!category.count) {
        setNotice(
          `${category.name} questions are being prepared. Please check back soon.`
        );
        return;
      }

      // The actual question is fetched individually by QuestionPlayer.
      setPuzzleGame(null);

      setSession({
        category: category.key,
        title: category.name,
        mode: "category",
      });
    });
  }

  // ------------------------------------------------------
  // RAPID FIRE
  // ------------------------------------------------------

  function playRapid(set, used) {
    gate(() => {
      setNotice("");
      setSession(null);
      setPuzzleGame(null);
      setRapid({ ...set, used });
    });
  }

  // ------------------------------------------------------
  // RENDER
  // ------------------------------------------------------

  return (
    <DashShell
      eyebrow="Arena // games"
      title={<ArenaTitle />}
      actions={state && <StatusPill status={state.status} />}
    >
      <ArenaNav />

      {!isPlayer && (
        <p
          className="glass mb-6 rounded-2xl px-5 py-4 text-sm text-white/70"
          data-testid="arena-play-signin-note"
        >
          Browse freely — sign in with your team or member account to play
          and earn XP.
        </p>
      )}

      {/* GAME SELECTION */}
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Choose your game</p>
          <p className="mt-2 text-sm text-white/45">
            Pick a challenge and test your skills.
          </p>
        </div>

        <span className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/30">
          SANKALP’26 // ARENA
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
        {state?.categories?.map((category) => (
          <CategoryCard
            key={category.key}
            category={category}
            onPlay={() => playCategory(category)}
          />
        ))}
      </div>

      {/* CATEGORY MESSAGE */}
      {notice && (
        <div
          role="status"
          className="mt-5 rounded-2xl border border-neon/30 bg-neon/5 px-5 py-4 text-sm leading-relaxed text-white/80"
        >
          <CheckCircle2 size={16} className="mr-2 inline text-neon" />
          {notice}
        </div>
      )}

      {/* QUESTION PRIVACY NOTE */}
      <div className="mt-6 rounded-2xl border border-white/[0.07] bg-white/[0.02] px-4 py-3">
        <p className="font-mono text-[9px] uppercase tracking-[0.2em] text-white/40">
          <span className="mr-2 text-ice">●</span>
          Challenges are revealed one at a time during gameplay.
        </p>
      </div>

      {/* RAPID FIRE */}
      <div className="mb-5 mt-12">
        <p className="eyebrow">Rapid fire</p>
        <p className="mt-2 text-sm text-white/45">
          Five questions · Sixty seconds.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {state?.rapid_sets?.map((set) => {
          const done = me?.rapid_done?.includes(set.key);
          const used = me?.rapid_used?.includes(set.key);
          const disabled = set.enabled === false;

          return (
            <button
              key={set.key}
              disabled={disabled}
              onClick={() => {
                if (!disabled) playRapid(set, used);
              }}
              data-testid={`arena-rapid-${set.key}`}
              className={`glass-strong glow-border card-scan rounded-3xl p-6 text-left transition-transform duration-300 ${
                disabled ? "cursor-not-allowed opacity-40" : "hover:-translate-y-1"
              }`}
            >
              <div className="flex items-center justify-between">
                <Timer size={22} className="text-neon" />

                <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">
                  {disabled
                    ? "Disabled"
                    : done
                    ? "XP claimed"
                    : used
                      ? "Practice"
                      : "≤ 50 XP"}
                </span>
              </div>

              <p className="mt-5 font-display text-xl font-bold uppercase tracking-wide text-white">
                {set.name}
              </p>

              <p className="text-sm text-white/50">{set.desc}</p>
            </button>
          );
        })}
      </div>

      {/* INDIVIDUAL QUESTION PLAYER */}
      {session && (
        <QuestionPlayer
          category={session.category}
          title={session.title}
          mode={session.mode}
          onClose={() => {
            setSession(null);
            refresh();
          }}
          onScored={reload}
        />
      )}

      {/* RAPID FIRE PLAYER */}
      {rapid && (
        <RapidPlayer
          set={rapid}
          used={rapid.used}
          onClose={() => {
            setRapid(null);
            refresh();
          }}
          onScored={reload}
        />
      )}

      {/* SUDOKU / KENKEN */}
      {puzzleGame && (
        <PuzzlePlayer
          game={puzzleGame}
          onClose={() => {
            setPuzzleGame(null);
            refresh();
          }}
          onScored={reload}
        />
      )}
    </DashShell>
  );
}
