
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Flame,
  Gamepad2,
  LogIn,
  Target,
  Trophy,
  Zap,
  LockKeyhole,
  Puzzle,
} from "lucide-react";

import DashShell from "@/components/DashShell";
import QuestionPlayer from "@/components/arena/QuestionPlayer";
import ChampionCard from "@/components/arena/ChampionCard";

import {
  AnimatedNumber,
  ArenaNav,
  BadgeChip,
  StatusPill,
  STATUS_COPY,
  useArena,
  CAT_ICONS,
} from "@/components/arena/arenaKit";

import { useCountdown } from "@/components/landing/Hero";
import { api } from "@/lib/api";

export const ArenaTitle = () => (
  <>
    <span className="font-wordmark font-black tracking-tight">
      <span className="wm-sankalp">ARENA</span>
    </span>

    <span className="mt-3 block font-display text-base font-bold uppercase text-white/80 spaced md:text-lg">
      Play. <span className="text-ice">Solve.</span>{" "}
      <span className="text-neon">Dominate.</span>
    </span>
  </>
);

// --------------------------------------------------------
// STAT CARD
// --------------------------------------------------------

const Stat = ({ label, children, icon: Icon, id }) => (
  <div
    className="glass glow-border rounded-3xl p-6"
    data-testid={`arena-stat-${id}`}
  >
    <p className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.3em] text-white/45">
      <Icon size={13} className="text-neon" />
      {label}
    </p>

    <div className="mt-3 font-wordmark text-4xl font-black text-white">
      {children}
    </div>
  </div>
);

// --------------------------------------------------------
// COUNTDOWN
// --------------------------------------------------------

function Countdown({ to, status }) {
  const [d, h, m, s] = useCountdown(
    to || new Date().toISOString()
  );

  return (
    <div className="glass rounded-3xl p-6" data-testid="arena-countdown">
      <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-white/45">
        {status === "upcoming" ? "Opens in" : "Arena closes in"}
      </p>

      {to && status !== "closed" && status !== "final" ? (
        <div className="mt-3 flex gap-5">
          {[[d, "D"], [h, "H"], [m, "M"], [s, "S"]].map(([value, label]) => (
            <div key={label}>
              <span className="font-display text-3xl font-bold tabular-nums text-white">
                {String(value).padStart(2, "0")}
              </span>

              <span className="ml-1 font-mono text-[10px] text-white/40">
                {label}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 font-display text-2xl font-bold uppercase text-white/70">
          {status === "final"
            ? "Final results"
            : status === "closed"
              ? "Scoring frozen"
              : "No closing time set"}
        </p>
      )}
    </div>
  );
}

// --------------------------------------------------------
// TOP FIVE LEADERBOARD
// --------------------------------------------------------

function Top5({ rows, meId }) {
  return (
    <div className="glass rounded-3xl p-6" data-testid="arena-top5">
      <div className="mb-4 flex items-center justify-between">
        <p className="eyebrow">Top 5</p>

        <Link
          to="/arena/leaderboard"
          className="font-mono text-[10px] uppercase tracking-[0.2em] text-ice hover:underline"
          data-testid="arena-top5-view-all"
        >
          View all
        </Link>
      </div>

      {rows.length === 0 ? (
        <p className="text-sm text-white/45">
          No XP earned yet — be the first on the board.
        </p>
      ) : (
        <ol className="space-y-2">
          {rows.slice(0, 5).map((row) => (
            <li
              key={row.user_id}
              className={`flex items-center justify-between rounded-xl px-3 py-2 ${
                row.user_id === meId
                  ? "bg-neon/10 ring-1 ring-neon/40"
                  : ""
              }`}
            >
              <span className="flex min-w-0 items-center gap-3">
                <span className="w-6 font-wordmark text-sm font-black text-white/60">
                  {row.rank}
                </span>

                <span className="truncate text-sm text-white">
                  {row.name}
                </span>
              </span>

              <span className="font-mono text-xs text-ice">
                {row.xp} XP
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

// --------------------------------------------------------
// PUBLIC INTRO
// --------------------------------------------------------

function PublicIntro({ state }) {
  const rules = state?.xp_rules;

  return (
    <div
      className="grid grid-cols-1 gap-6 lg:grid-cols-[1.3fr_1fr]"
      data-testid="arena-public-intro"
    >
      <div className="glass-strong glow-border rounded-[2rem] p-8">
        <p className="eyebrow mb-4">How it works</p>

        <p className="text-lg text-white/75">
          Take a break. Challenge your brain. Climb the leaderboard.
          Registered team leaders and team members can play puzzles,
          quizzes, debugging and rapid-fire rounds to earn XP during
          SANKALP'26.
        </p>

        {rules && (
          <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {[
              ["Easy", rules.easy],
              ["Medium", rules.medium],
              ["Hard", rules.hard],
              ["Rapid fire", `≤${rules.rapid_max}`],
              ["Category cleared", rules.milestone],
              ["Daily bonus", rules.daily],
            ].map(([label, value]) => (
              <div
                key={label}
                className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
              >
                <p className="font-wordmark text-xl font-black text-white">
                  {value} XP
                </p>

                <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/45">
                  {label}
                </p>
              </div>
            ))}
          </div>
        )}

        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to="/auth?mode=login"
            className="btn-neon"
            data-testid="arena-signin-cta"
          >
            <LogIn size={16} />
            Sign in to play
          </Link>

          <Link
            to="/arena/play"
            className="btn-ghost"
            data-testid="arena-browse-cta"
          >
            Browse games
          </Link>
        </div>
      </div>

      <div className="space-y-6">
        <Countdown
          to={
            state?.status === "upcoming"
              ? state?.starts_at
              : state?.closes_at
          }
          status={state?.status}
        />

        <div className="glass rounded-3xl p-6">
          <p className="eyebrow mb-4">Badges to unlock</p>

          <div className="flex flex-wrap gap-2">
            {state?.badges.map((badge) => (
              <span
                key={badge.key}
                className="rounded-full border border-white/10 px-3 py-1 text-xs text-white/65"
              >
                {badge.name}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// --------------------------------------------------------
// MAIN ARENA DASHBOARD
// --------------------------------------------------------

export default function ArenaHome() {
  const { state, me, reload, isPlayer, user } = useArena();

  const [board, setBoard] = useState([]);
  const [dailyOpen, setDailyOpen] = useState(false);

  // Public leaderboard refresh.
  useEffect(() => {
    const load = () =>
      api
        .get("/arena/leaderboard")
        .then((response) => setBoard(response.data.rows))
        .catch(() => {});

    load();

    const timer = setInterval(load, 10000);

    return () => clearInterval(timer);
  }, []);

  const status = state?.status;

  return (
    <DashShell
      eyebrow="SANKALP'26 // games & XP"
      title={<ArenaTitle />}
      actions={status && <StatusPill status={status} />}
    >
      <ArenaNav />

      {state?.champion && (
        <ChampionCard
          champion={state.champion}
          prize={state.prize}
          announcement={state.announcement}
        />
      )}

      {status && status !== "live" && !state?.champion && (
        <p
          className="glass mb-6 rounded-2xl px-5 py-4 text-sm text-white/70"
          data-testid="arena-status-banner"
        >
          {STATUS_COPY[status][1]}
        </p>
      )}

      {!isPlayer && user && (
        <p
          className="glass mb-6 rounded-2xl px-5 py-4 text-sm text-white/70"
          data-testid="arena-staff-note"
        >
          You're signed in as {user.role}. Staff accounts can browse the
          Arena but can't earn XP.
        </p>
      )}

      {!isPlayer ? (
        <PublicIntro state={state} />
      ) : (
        me &&
        state && (
          <div
            className="space-y-6"
            data-testid="arena-player-dashboard"
          >
            {/* ACCOUNT STATUS */}
            {me.disqualified && (
              <p className="rounded-2xl border border-neon/50 bg-neon/10 px-5 py-4 text-sm text-neon">
                Scoring is disabled for this account. Contact the organisers.
              </p>
            )}

            {/* WELCOME */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-base text-white/60 md:text-lg"
            >
              Welcome, <span className="text-white">{me.name}</span>
              {me.team_name && <> · Team {me.team_name}</>}.{" "}
              <span className="text-neon">
                Every challenge counts. Every point brings you closer to
                victory.
              </span>
            </motion.p>

            {/* PLAYER STATS */}
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              <Stat label="My XP" icon={Zap} id="xp">
                <AnimatedNumber
                  value={me.xp}
                  className="text-grad"
                  testid="arena-my-xp"
                />
              </Stat>

              <Stat label="My rank" icon={Trophy} id="rank">
                <span data-testid="arena-my-rank">
                  {me.rank ? `#${me.rank}` : "—"}
                </span>

                <span className="ml-2 font-mono text-xs text-white/40">
                  of {me.participants}
                </span>
              </Stat>

              <Stat label="Completed" icon={Target} id="completed">
                <AnimatedNumber
                  value={me.completed}
                  testid="arena-my-completed"
                />
              </Stat>

              <Stat label="Badges" icon={Flame} id="badges">
                <span data-testid="arena-my-badges">
                  {me.badges.length}
                </span>

                <span className="ml-2 font-mono text-xs text-white/40">
                  / {state.badges.length}
                </span>
              </Stat>
            </div>

            {/* PLAY NOW AND DAILY CHALLENGE */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <Link
                to="/arena/play"
                data-testid="arena-play-now"
                className="glass-strong glow-border card-scan group relative overflow-hidden rounded-[2rem] p-8 transition-transform duration-500 hover:-translate-y-1 lg:col-span-2"
              >
                <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-neon/20 blur-[90px]" />

                <Gamepad2 size={34} className="text-neon" />

                <p className="mt-6 font-editorial text-3xl font-extrabold uppercase text-white sm:text-4xl">
                  Play now
                </p>

                <p className="mt-2 max-w-md text-white/60">
                  Explore logic puzzles, aptitude, technical challenges,
                  Sudoku, KenKen and rapid-fire rounds.
                </p>

                <span className="mt-6 inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.25em] text-ice">
                  Enter the games
                  <ArrowRight
                    size={14}
                    className="transition-transform group-hover:translate-x-1"
                  />
                </span>
              </Link>

              {/* DAILY CHALLENGE — QUESTION HIDDEN */}
              {state.daily?.available && (
                <div
                  className="glass glow-border relative overflow-hidden rounded-[2rem] p-7"
                  data-testid="arena-daily-card"
                >
                  <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-ice/10 blur-[65px]" />

                  <div className="relative">
                    <div className="flex items-center justify-between gap-2">
                      <p className="eyebrow">
                        Daily challenge
                      </p>

                      <span className="rounded-full border border-ice/25 bg-ice/10 px-3 py-1 font-mono text-[9px] uppercase tracking-wider text-ice">
                        +{state.daily.bonus} XP
                      </span>
                    </div>

                    <div className="mt-6 flex h-12 w-12 items-center justify-center rounded-2xl border border-ice/25 bg-ice/10 text-ice">
                      <LockKeyhole size={23} />
                    </div>

                    <p className="mt-5 font-display text-lg font-bold leading-snug text-white">
                      Today's challenge is waiting.
                    </p>

                    <p className="mt-2 text-sm leading-relaxed text-white/50">
                      A new challenge is selected every day. Unlock it when
                      you're ready to test yourself.
                    </p>

                    <p className="mt-3 font-mono text-[9px] uppercase tracking-[0.2em] text-white/35">
                      {state.daily.date}
                    </p>

                    <button
                      onClick={() => setDailyOpen(true)}
                      className={
                        me.daily_done
                          ? "btn-ghost mt-6 w-full"
                          : "btn-neon mt-6 w-full"
                      }
                      data-testid="arena-daily-play"
                    >
                      {me.daily_done
                        ? "Replay (practice)"
                        : "Take the challenge"}
                      <ArrowRight size={15} />
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* COUNTDOWN, LEADERBOARD, CATEGORY PROGRESS */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <Countdown
                to={
                  status === "upcoming"
                    ? state.starts_at
                    : state.closes_at
                }
                status={status}
              />

              <Top5 rows={board} meId={user.id} />

              <div className="glass rounded-3xl p-6" data-testid="arena-progress">
                <p className="eyebrow mb-4">Category progress</p>

                <div className="space-y-3">
                  {state.categories.map((category) => {
                    const progress = me.categories[category.key];
                    const Icon =
                      CAT_ICONS?.[category.key] || Puzzle;

                    return (
                      <div key={category.key}>
                        <div className="mb-1 flex justify-between text-xs">
                          <span className="flex items-center gap-2 text-white/75">
                            <Icon size={12} className="text-ice" />
                            {category.name}
                          </span>

                          <span className="font-mono text-white/45">
                            {progress.correct}/{progress.total}
                          </span>
                        </div>

                        <div className="h-1.5 rounded-full bg-white/10">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{
                              width: `${
                                progress.total
                                  ? (progress.attempted / progress.total) * 100
                                  : 0
                              }%`,
                            }}
                            transition={{ duration: 1 }}
                            className="h-1.5 rounded-full bg-gradient-to-r from-cerulean to-neon"
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* ACHIEVEMENTS */}
            <div className="glass rounded-3xl p-6">
              <p className="eyebrow mb-4">My achievements</p>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                {state.badges.map((badge) => (
                  <BadgeChip
                    key={badge.key}
                    badge={badge}
                    earned={me.badges.includes(badge.key)}
                  />
                ))}
              </div>
            </div>

            {/* ACTIVITY HISTORY */}
            <div
              className="glass rounded-3xl p-6"
              data-testid="arena-history"
            >
              <p className="eyebrow mb-4">Activity history</p>

              {me.history.length === 0 ? (
                <p className="text-sm text-white/45">
                  No XP yet. Your first correct answer unlocks First Blood.
                </p>
              ) : (
                <ul className="divide-y divide-white/5">
                  {me.history.map((item) => (
                    <li
                      key={item.ref}
                      className="flex items-center justify-between gap-4 py-3 text-sm"
                    >
                      <span className="min-w-0 truncate text-white/75">
                        {item.reason}
                      </span>

                      <span className="flex shrink-0 items-center gap-4">
                        <span className="font-mono text-[10px] text-white/35">
                          {new Date(item.created_at).toLocaleString()}
                        </span>

                        <span className="font-mono text-ice">
                          +{item.amount}
                        </span>
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )
      )}

      {/* DAILY QUESTION PLAYER */}
      {dailyOpen && (
        <QuestionPlayer
          title="Daily challenge"
          mode="daily"
          onClose={() => {
            setDailyOpen(false);
            reload();
          }}
          onScored={reload}
        />
      )}
    </DashShell>
  );
}
