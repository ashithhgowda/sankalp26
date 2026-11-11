
import { useEffect, useState } from "react";
import {
  CalendarClock,
  CheckCircle2,
  Clock,
  Crown,
  Gamepad2,
  Lock,
  Pause,
  Play,
  RotateCcw,
  Save,
  ShieldAlert,
  Snowflake,
  Trophy,
  Unlock,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { Switch } from "@/components/ui/switch";
import { api, formatErr } from "@/lib/api";
import ArenaQuestions from "@/pages/admin/ArenaQuestions";

const GAME_MODES = [
  { key: "logic", label: "Brain Teasers & Logic" },
  { key: "kenken", label: "KenKen" },
  { key: "predict", label: "Predict the Output" },
  { key: "sudoku", label: "Sudoku" },
  { key: "rapid", label: "Rapid Fire" },
];

const DEFAULT_GAMES = {
  logic: true,
  kenken: true,
  predict: true,
  sudoku: true,
  rapid: true,
};

const DEFAULT_XP = {
  easy: 10,
  medium: 20,
  hard: 35,
};

const toLocal = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return new Date(
    d.getTime() - d.getTimezoneOffset() * 60000
  ).toISOString().slice(0, 16);
};

const fromLocal = (value) =>
  value ? new Date(value).toISOString() : null;

function SectionTitle({ icon: Icon, title, subtitle }) {
  return (
    <div className="mb-5 flex items-start gap-3">
      <div className="rounded-xl border border-ice/20 bg-ice/5 p-3">
        <Icon size={20} className="text-ice" />
      </div>
      <div>
        <h3 className="font-display text-lg font-bold uppercase text-white">
          {title}
        </h3>
        {subtitle && (
          <p className="mt-1 text-xs text-white/45">{subtitle}</p>
        )}
      </div>
    </div>
  );
}

function SettingsCard({ s, reload }) {
  const [f, setF] = useState({
    starts_at: toLocal(s.starts_at),
    closes_at: toLocal(s.closes_at),
    prize: s.prize || "",
    announcement: s.announcement || "",
  });

  useEffect(() => {
    setF({
      starts_at: toLocal(s.starts_at),
      closes_at: toLocal(s.closes_at),
      prize: s.prize || "",
      announcement: s.announcement || "",
    });
  }, [s.starts_at, s.closes_at, s.prize, s.announcement]);

  const save = async (e) => {
    e.preventDefault();

    if (
      f.starts_at &&
      f.closes_at &&
      new Date(f.closes_at) <= new Date(f.starts_at)
    ) {
      toast.error("Closing time must be after opening time.");
      return;
    }

    try {
      await api.put("/arena/admin/settings", {
        ...f,
        starts_at: fromLocal(f.starts_at),
        closes_at: fromLocal(f.closes_at),
      });

      toast.success("Arena schedule saved.");
      reload();
    } catch (error) {
      toast.error(formatErr(error));
    }
  };

  return (
    <form
      onSubmit={save}
      className="glass-strong space-y-5 rounded-3xl p-6"
      data-testid="arena-admin-settings-form"
    >
      <SectionTitle
        icon={CalendarClock}
        title="Arena Schedule"
        subtitle="Configure the automatic opening and closing time."
      />

      <div className="rounded-xl border border-ice/15 bg-ice/5 px-4 py-3">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-ice">
          Time zone
        </p>
        <p className="mt-1 text-sm text-white">
          India Standard Time · Asia/Kolkata
        </p>
        <p className="mt-1 text-xs text-white/40">
          Times are entered using your browser's local time.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <label>
          <span className="field-label">Opening date and time</span>
          <input
            type="datetime-local"
            className="field"
            value={f.starts_at}
            onChange={(e) =>
              setF({ ...f, starts_at: e.target.value })
            }
            data-testid="arena-admin-starts-input"
          />
          <span className="mt-1 block text-[10px] text-white/35">
            Leave blank to allow immediate opening.
          </span>
        </label>

        <label>
          <span className="field-label">Closing date and time</span>
          <input
            type="datetime-local"
            className="field"
            value={f.closes_at}
            onChange={(e) =>
              setF({ ...f, closes_at: e.target.value })
            }
            required
            data-testid="arena-admin-closes-input"
          />
        </label>
      </div>

      <label className="block">
        <span className="field-label">Arena Champion prize</span>
        <input
          className="field"
          placeholder="e.g. Goodies hamper + certificate"
          value={f.prize}
          onChange={(e) =>
            setF({ ...f, prize: e.target.value })
          }
          data-testid="arena-admin-prize-input"
        />
      </label>

      <label className="block">
        <span className="field-label">Winner announcement</span>
        <textarea
          className="field min-h-[80px]"
          value={f.announcement}
          onChange={(e) =>
            setF({ ...f, announcement: e.target.value })
          }
          data-testid="arena-admin-announcement-input"
        />
      </label>

      <button className="btn-neon" data-testid="arena-admin-save-settings">
        <Save size={15} />
        Save schedule
      </button>
    </form>
  );
}

function OperationsCard({ s, reload, participants }) {
  const [tie, setTie] = useState(null);
  const [busy, setBusy] = useState(false);

  const act = async (fn, message) => {
    if (busy) return;

    setBusy(true);
    try {
      await fn();
      toast.success(message);
      await reload();
    } catch (error) {
      toast.error(formatErr(error));
    } finally {
      setBusy(false);
    }
  };

  const finalize = async (champion_user_id = null) => {
    try {
      setBusy(true);

      const { data } = await api.post(
        "/arena/admin/finalize",
        { champion_user_id }
      );

      if (data.tie) {
        setTie(data.candidates);
        toast.warning("Tie at #1. Select the Arena Champion.");
      } else {
        setTie(null);
        toast.success(`${data.champion.name} is the Arena Champion!`);
      }

      await reload();
    } catch (error) {
      toast.error(formatErr(error));
    } finally {
      setBusy(false);
    }
  };

  const tied =
    tie ||
    (s.tie_candidates?.length
      ? participants.filter((p) =>
          s.tie_candidates.includes(p.user_id)
        )
      : null);

  const statusColors = {
    live: "text-ice",
    upcoming: "text-[#FFCF5A]",
    paused: "text-neon",
    closed: "text-white/50",
    final: "text-[#FFCF5A]",
  };

  const canFinalize =
    !s.finalized &&
    s.frozen &&
    s.status !== "live" &&
    s.status !== "upcoming";

  return (
    <div
      className="glass-strong space-y-5 rounded-3xl p-6"
      data-testid="arena-admin-control"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SectionTitle
          icon={Play}
          title="Live Operations"
          subtitle="Start, pause, resume or close the competition."
        />

        <span
          className={`font-mono text-xs font-bold uppercase tracking-[0.2em] ${
            statusColors[s.status] || "text-white"
          }`}
          data-testid="arena-admin-status"
        >
          {s.status}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {s.status === "upcoming" && (
          <button
            onClick={() =>
              act(
                () => api.post("/arena/admin/start-now"),
                "Arena started."
              )
            }
            disabled={busy}
            className="btn-neon"
            data-testid="arena-admin-start-now"
          >
            <Play size={15} />
            Start Arena Now
          </button>
        )}

        {s.status === "live" && (
          <button
            onClick={() =>
              act(
                () => api.post("/arena/admin/pause"),
                "Arena paused."
              )
            }
            disabled={busy}
            className="btn-ghost"
            data-testid="arena-admin-pause"
          >
            <Pause size={15} />
            Pause Arena
          </button>
        )}

        {s.status === "paused" && (
          <button
            onClick={() =>
              act(
                () => api.post("/arena/admin/resume"),
                "Arena resumed."
              )
            }
            disabled={busy}
            className="btn-neon"
            data-testid="arena-admin-resume"
          >
            <Play size={15} />
            Resume Arena
          </button>
        )}

        {!["closed", "final"].includes(s.status) && (
          <button
            onClick={() =>
              window.confirm(
                "Permanently close the Arena? This stops all scoring."
              ) &&
              act(
                () => api.post("/arena/admin/close"),
                "Arena permanently closed."
              )
            }
            disabled={busy}
            className="btn-ghost border-neon/30 text-neon"
            data-testid="arena-admin-close"
          >
            <Lock size={15} />
            Close Arena
          </button>
        )}

        {s.frozen ? (
          <button
            onClick={() =>
              act(
                () => api.post("/arena/admin/freeze", { value: false }),
                "Scoring unfrozen."
              )
            }
            disabled={busy || s.finalized || s.manually_closed}
            className="btn-ghost"
            data-testid="arena-admin-unfreeze"
          >
            <Unlock size={15} />
            Unfreeze Scoring
          </button>
        ) : (
          <button
            onClick={() =>
              act(
                () => api.post("/arena/admin/freeze", { value: true }),
                "Scoring frozen."
              )
            }
            disabled={busy || s.finalized}
            className="btn-ghost"
            data-testid="arena-admin-freeze"
          >
            <Snowflake size={15} />
            Freeze Scoring
          </button>
        )}

        {(s.finalized || s.manually_closed) && (
          <button
            onClick={() =>
              window.confirm(
                "Reopen the Arena? This removes the champion announcement and unfreezes scoring."
              ) &&
              act(
                () => api.post("/arena/admin/reopen"),
                "Arena reopened. Check the schedule before starting."
              )
            }
            disabled={busy}
            className="btn-ghost"
            data-testid="arena-admin-reopen"
          >
            <RotateCcw size={15} />
            Reopen Arena
          </button>
        )}
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">
          Current status
        </p>

        <p className="mt-2 text-sm text-white/75">
          {s.status === "live" &&
            "Arena is live. Participants can play enabled games and earn XP."}
          {s.status === "upcoming" &&
            "Arena is waiting for its scheduled opening time."}
          {s.status === "paused" &&
            "Gameplay is temporarily paused. Resume when ready."}
          {s.status === "closed" &&
            "Arena is closed. No further XP can be earned."}
          {s.status === "final" &&
            "Competition is finalized and the champion has been declared."}
        </p>

        {s.frozen && s.status !== "final" && (
          <p className="mt-2 text-xs text-neon">
            Scoring is frozen independently of the Arena status.
          </p>
        )}
      </div>

      {s.champion && (
        <div
          className="rounded-2xl border border-[#FFCF5A]/25 bg-[#FFCF5A]/5 p-4"
          data-testid="arena-admin-champion"
        >
          <p className="flex items-center gap-2 font-display font-bold uppercase text-[#FFCF5A]">
            <Trophy size={17} />
            Arena Champion
          </p>

          <p className="mt-2 text-sm text-white">
            {s.champion.name} · {s.champion.xp} XP
          </p>

          {s.champion.tie_resolved_by_admin && (
            <p className="mt-1 text-xs text-white/40">
              Tie resolved by admin.
            </p>
          )}
        </div>
      )}

      {!s.finalized && (
        <button
          onClick={() => finalize(null)}
          disabled={busy || !canFinalize}
          className="btn-neon disabled:cursor-not-allowed disabled:opacity-30"
          data-testid="arena-admin-finalize"
        >
          <Crown size={15} />
          Finalize Arena Champion
        </button>
      )}

      {tied && !s.finalized && (
        <div
          className="rounded-2xl border border-neon/50 bg-neon/10 p-4"
          data-testid="arena-admin-tie-review"
        >
          <p className="flex items-center gap-2 text-sm text-neon">
            <ShieldAlert size={15} />
            Tie at #1. Review and choose the champion:
          </p>

          <div className="mt-3 space-y-2">
            {tied.map((candidate) => (
              <div
                key={candidate.user_id}
                className="flex items-center justify-between gap-3 text-sm text-white/80"
              >
                <span>
                  {candidate.name} · {candidate.xp} XP ·{" "}
                  {candidate.completed} completed
                </span>

                <button
                  onClick={() => finalize(candidate.user_id)}
                  disabled={busy}
                  className="btn-ghost !px-4 !py-1.5 !text-[10px]"
                  data-testid={`arena-admin-pick-${candidate.user_id}`}
                >
                  Declare
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs leading-relaxed text-white/40">
        Freeze scoring before finalizing. Finalization calculates the champion
        from the verified leaderboard and locks the competition.
      </p>
    </div>
  );
}

function GameControls({ s, reload }) {
  const [busyGame, setBusyGame] = useState("");

  const games = s.enabled_games || DEFAULT_GAMES;

  const toggle = async (key, value) => {
    if (busyGame) return;

    setBusyGame(key);
    try {
      await api.put("/arena/admin/controls", {
        enabled_games: { [key]: value },
      });

      toast.success(
        `${GAME_MODES.find((game) => game.key === key)?.label} ${
          value ? "enabled" : "disabled"
        }.`
      );

      await reload();
    } catch (error) {
      toast.error(formatErr(error));
    } finally {
      setBusyGame("");
    }
  };

  return (
    <div className="glass-strong rounded-3xl p-6">
      <SectionTitle
        icon={Gamepad2}
        title="Game Availability"
        subtitle="Enable or disable each Arena game independently."
      />

      <div className="space-y-4">
        {GAME_MODES.map((game) => {
          const enabled = games[game.key] !== false;

          return (
            <div
              key={game.key}
              className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/[0.025] p-4"
            >
              <div>
                <p className="text-sm font-semibold text-white">
                  {game.label}
                </p>
                <p className="mt-1 text-[10px] uppercase tracking-[0.15em] text-white/40">
                  {busyGame === game.key
                    ? "Saving..."
                    : enabled
                      ? "Available to participants"
                      : "Disabled for participants"}
                </p>
              </div>

              <Switch
                checked={enabled}
                disabled={!!busyGame}
                onCheckedChange={(value) => toggle(game.key, value)}
                data-testid={`arena-game-toggle-${game.key}`}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ScoringControls({ s, reload }) {
  const [f, setF] = useState({
    difficulty_xp: {
      ...DEFAULT_XP,
      ...(s.difficulty_xp || {}),
    },
    daily_enabled: s.daily_enabled !== false,
    daily_xp: s.daily_xp ?? 10,
    rapid_correct_xp: s.rapid_correct_xp ?? 8,
    rapid_time_bonus_max: s.rapid_time_bonus_max ?? 10,
  });

  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setF({
      difficulty_xp: {
        ...DEFAULT_XP,
        ...(s.difficulty_xp || {}),
      },
      daily_enabled: s.daily_enabled !== false,
      daily_xp: s.daily_xp ?? 10,
      rapid_correct_xp: s.rapid_correct_xp ?? 8,
      rapid_time_bonus_max: s.rapid_time_bonus_max ?? 10,
    });
  }, [
    s.difficulty_xp,
    s.daily_enabled,
    s.daily_xp,
    s.rapid_correct_xp,
    s.rapid_time_bonus_max,
  ]);

  const setXp = (level, value) => {
    setF((previous) => ({
      ...previous,
      difficulty_xp: {
        ...previous.difficulty_xp,
        [level]: value,
      },
    }));
  };

  const save = async (e) => {
    e.preventDefault();

    const numericValues = [
      ...Object.values(f.difficulty_xp),
      f.daily_xp,
      f.rapid_correct_xp,
      f.rapid_time_bonus_max,
    ];

    if (
      numericValues.some(
        (value) =>
          !Number.isInteger(Number(value)) ||
          Number(value) < 0
      )
    ) {
      toast.error("All XP values must be non-negative whole numbers.");
      return;
    }

    if (
      Object.values(f.difficulty_xp).some((value) => value > 100) ||
      f.daily_xp > 50 ||
      f.rapid_correct_xp > 20 ||
      f.rapid_time_bonus_max > 20
    ) {
      toast.error("One or more XP values exceed the allowed limits.");
      return;
    }

    setBusy(true);

    try {
      await api.put("/arena/admin/controls", {
        difficulty_xp: {
          easy: Number(f.difficulty_xp.easy),
          medium: Number(f.difficulty_xp.medium),
          hard: Number(f.difficulty_xp.hard),
        },
        daily_enabled: f.daily_enabled,
        daily_xp: Number(f.daily_xp),
        rapid_correct_xp: Number(f.rapid_correct_xp),
        rapid_time_bonus_max: Number(f.rapid_time_bonus_max),
      });

      toast.success("Arena scoring settings saved.");
      await reload();
    } catch (error) {
      toast.error(formatErr(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form
      onSubmit={save}
      className="glass-strong space-y-5 rounded-3xl p-6"
      data-testid="arena-admin-scoring-form"
    >
      <SectionTitle
        icon={Zap}
        title="Scoring Configuration"
        subtitle="Configure XP rewards for Arena challenges."
      />

      <div>
        <p className="field-label mb-3">Difficulty-based XP</p>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {["easy", "medium", "hard"].map((level) => (
            <label key={level}>
              <span className="field-label capitalize">{level}</span>
              <div className="relative">
                <input
                  type="number"
                  min="0"
                  max="100"
                  className="field pr-12"
                  value={f.difficulty_xp[level]}
                  onChange={(e) => setXp(level, e.target.value)}
                  data-testid={`arena-xp-${level}`}
                />
                <span className="absolute right-3 top-3 text-xs text-ice">
                  XP
                </span>
              </div>
            </label>
          ))}
        </div>
        <p className="mt-2 text-[10px] text-white/35">
          Applied to question-based challenges and new Sudoku/KenKen puzzles.
        </p>
      </div>

      <div className="rounded-2xl border border-white/10 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-white">
              Daily Challenge
            </p>
            <p className="mt-1 text-xs text-white/40">
              Enable or disable the daily bonus challenge.
            </p>
          </div>

          <Switch
            checked={f.daily_enabled}
            onCheckedChange={(value) =>
              setF({ ...f, daily_enabled: value })
            }
            data-testid="arena-daily-toggle"
          />
        </div>

        <label className="mt-4 block max-w-xs">
          <span className="field-label">Daily bonus XP</span>
          <input
            type="number"
            min="0"
            max="50"
            className="field"
            value={f.daily_xp}
            onChange={(e) =>
              setF({ ...f, daily_xp: e.target.value })
            }
            disabled={!f.daily_enabled}
            data-testid="arena-daily-xp"
          />
        </label>
      </div>

      <div className="rounded-2xl border border-white/10 p-4">
        <p className="mb-4 text-sm font-semibold text-white">
          Rapid Fire rewards
        </p>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label>
            <span className="field-label">XP per correct answer</span>
            <input
              type="number"
              min="0"
              max="20"
              className="field"
              value={f.rapid_correct_xp}
              onChange={(e) =>
                setF({ ...f, rapid_correct_xp: e.target.value })
              }
              data-testid="arena-rapid-correct-xp"
            />
          </label>

          <label>
            <span className="field-label">Maximum time bonus XP</span>
            <input
              type="number"
              min="0"
              max="20"
              className="field"
              value={f.rapid_time_bonus_max}
              onChange={(e) =>
                setF({ ...f, rapid_time_bonus_max: e.target.value })
              }
              data-testid="arena-rapid-time-bonus"
            />
          </label>
        </div>

        <p className="mt-2 text-xs text-white/40">
          Rapid Fire remains capped at 50 XP per scored run.
          The time bonus is available when at least four answers are correct.
        </p>
      </div>

      <button
        className="btn-neon"
        disabled={busy}
        data-testid="arena-admin-save-scoring"
      >
        <Save size={15} />
        {busy ? "Saving..." : "Save Scoring Settings"}
      </button>
    </form>
  );
}

function Participants({ rows, reload }) {
  const dq = async (participant, value) => {
    try {
      await api.post(
        `/arena/admin/participants/${participant.user_id}/disqualify`,
        { value }
      );

      toast.success(
        value ? "Excluded from leaderboard." : "Participant reinstated."
      );

      reload();
    } catch (error) {
      toast.error(formatErr(error));
    }
  };

  if (!rows.length) {
    return (
      <p className="glass rounded-3xl p-8 text-center text-white/50">
        No participant activity yet.
      </p>
    );
  }

  return (
    <div
      className="glass overflow-x-auto rounded-3xl"
      data-testid="arena-admin-participants"
    >
      <table className="w-full min-w-[820px] text-left text-sm">
        <thead>
          <tr className="border-b border-white/10 font-mono text-[10px] uppercase tracking-[0.25em] text-white/40">
            <th className="px-5 py-4">Rank</th>
            <th className="px-4 py-4">Participant</th>
            <th className="px-4 py-4">XP</th>
            <th className="px-4 py-4">Done</th>
            <th className="px-4 py-4">Accuracy</th>
            <th className="px-4 py-4">Flags</th>
            <th className="px-5 py-4">Excluded</th>
          </tr>
        </thead>

        <tbody>
          {rows.map((p) => (
            <tr
              key={p.user_id}
              className={`border-b border-white/5 ${
                p.flags.length ? "bg-neon/[0.06]" : ""
              }`}
              data-testid={`arena-admin-participant-${p.user_id}`}
            >
              <td className="px-5 py-3 font-mono text-white/60">
                {p.disqualified ? "—" : p.rank}
              </td>

              <td className="px-4 py-3 text-white">
                {p.name}
                <p className="text-xs text-white/40">{p.team_name}</p>
              </td>

              <td className="px-4 py-3 font-mono text-ice">{p.xp}</td>
              <td className="px-4 py-3 font-mono text-white/70">
                {p.completed}
              </td>

              <td className="px-4 py-3 font-mono text-white/70">
                {p.accuracy}%{" "}
                <span className="text-white/35">({p.attempts})</span>
              </td>

              <td className="px-4 py-3 text-xs text-neon">
                {p.flags.length ? (
                  p.flags.join(" · ")
                ) : (
                  <span className="text-white/30">—</span>
                )}
              </td>

              <td className="px-5 py-3">
                <Switch
                  checked={p.disqualified}
                  onCheckedChange={(value) => dq(p, value)}
                  data-testid={`arena-admin-dq-${p.user_id}`}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ArenaAdmin() {
  const [s, setS] = useState(null);
  const [parts, setParts] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    const [settings, participants] = await Promise.all([
      api.get("/arena/admin/settings"),
      api.get("/arena/admin/participants"),
    ]);

    setS(settings.data);
    setParts(participants.data);
    setLoading(false);
  };

  useEffect(() => {
    load().catch((error) => {
      setLoading(false);
      toast.error(formatErr(error));
    });
  }, []);

  if (loading) {
    return <p className="text-white/40">Loading Arena controls...</p>;
  }

  if (!s) {
    return (
      <p className="glass rounded-2xl p-6 text-white/50">
        Unable to load Arena settings. Refresh the page and try again.
      </p>
    );
  }

  return (
    <div className="space-y-7" data-testid="arena-admin">
      <div className="glass-strong rounded-3xl p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="eyebrow">SANKALP'26 // Arena administration</p>
            <h2 className="mt-2 font-editorial text-3xl font-extrabold uppercase text-white">
              Arena <span className="text-grad">Control Center</span>
            </h2>
          </div>

          <button onClick={() => load()} className="btn-ghost">
            <RotateCcw size={14} />
            Refresh
          </button>
        </div>

        <p className="mt-3 max-w-3xl text-sm text-white/50">
          Control the Arena schedule, game availability, scoring rules,
          participant leaderboard and Arena Champion.
        </p>
      </div>

      {/* SCHEDULE AND OPERATIONS */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <SettingsCard s={s} reload={load} />
        <OperationsCard s={s} reload={load} participants={parts} />
      </div>

      {/* GAME AVAILABILITY AND SCORING */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <GameControls s={s} reload={load} />
        <ScoringControls s={s} reload={load} />
      </div>

      {/* PARTICIPANTS */}
      <section className="space-y-4">
        <SectionTitle
          icon={Trophy}
          title="Participants & Leaderboard"
          subtitle="Review XP, ranking, accuracy and participant eligibility."
        />
        <Participants rows={parts} reload={load} />
      </section>

      {/* QUESTION BANK */}
      <section className="space-y-4">
        <SectionTitle
          icon={CalendarClock}
          title="Question Bank Management"
          subtitle="Create, edit, publish or remove Arena challenges."
        />
        <ArenaQuestions />
      </section>
    </div>
  );
}
