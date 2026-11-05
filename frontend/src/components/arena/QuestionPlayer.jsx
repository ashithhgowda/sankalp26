
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowRight,
  Check,
  Loader2,
  X,
  Trophy,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";

import { api, formatErr } from "@/lib/api";
import { beep, burst } from "@/lib/arenaFx";
import { CAT_ICONS, DIFF_STYLE } from "@/components/arena/arenaKit";

// --------------------------------------------------------
// CODE DISPLAY
// --------------------------------------------------------

export const CodeBlock = ({ code, lang }) => (
  <pre
    className="mt-5 overflow-x-auto rounded-2xl border border-white/10 bg-black/60 p-5 font-mono text-[13px] leading-relaxed text-[#cfe9ff]"
    data-testid="question-code-block"
  >
    {lang && (
      <span className="mb-3 block font-mono text-[10px] uppercase tracking-[0.3em] text-neon">
        {lang}
      </span>
    )}
    <code>{code}</code>
  </pre>
);

// --------------------------------------------------------
// XP ANIMATION
// --------------------------------------------------------

export const XpFlash = ({ xp }) => (
  <AnimatePresence>
    {xp > 0 && (
      <motion.div
        key={xp}
        initial={{ opacity: 0, y: 20, scale: 0.6 }}
        animate={{ opacity: 1, y: -10, scale: 1 }}
        exit={{ opacity: 0 }}
        transition={{ type: "spring", stiffness: 260, damping: 14 }}
        data-testid="xp-flash"
        className="pointer-events-none font-wordmark text-4xl font-black text-grad drop-shadow-[0_0_20px_rgba(255,45,149,.6)]"
      >
        +{xp} XP
      </motion.div>
    )}
  </AnimatePresence>
);

// --------------------------------------------------------
// ANSWER OPTION
// --------------------------------------------------------

export const Option = ({
  i,
  text,
  state,
  onClick,
  disabled,
}) => {
  const tones = {
    picked: "border-ice bg-cerulean/20",
    right: "border-ice bg-ice/15 text-white",
    wrong: "border-neon bg-neon/15",
    idle: "border-white/10 hover:border-white/30 bg-white/[0.03]",
  };

  const tone = tones[state] || tones.idle;

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      data-testid={`question-option-${i}`}
      className={`flex w-full items-center gap-4 rounded-2xl border px-5 py-4 text-left text-sm text-white/85 transition-[border-color,background-color,transform] duration-200 enabled:hover:-translate-y-0.5 ${tone}`}
    >
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border border-white/15 font-mono text-[11px] text-white/60">
        {state === "right" ? (
          <Check size={14} className="text-ice" />
        ) : state === "wrong" ? (
          <X size={14} className="text-neon" />
        ) : (
          i + 1
        )}
      </span>

      <span className="whitespace-pre-wrap">{text}</span>
    </button>
  );
};

// --------------------------------------------------------
// MISSION BRIEFING
// --------------------------------------------------------

function Intro({
  title,
  mode,
  onStart,
  loading,
}) {
  const isDaily = mode === "daily";

  return (
    <div data-testid="player-intro">
      <p className="eyebrow mb-3">
        {isDaily ? "Daily mission" : "Mission briefing"}
      </p>

      <h2 className="font-editorial text-3xl font-extrabold uppercase text-white">
        {title}
      </h2>

      <ul className="mt-6 space-y-3 text-sm leading-relaxed text-white/65">
        {isDaily ? (
          <>
            <li>• One special challenge selected for today.</li>
            <li>• Earn bonus XP for a correct answer during the live Arena.</li>
            <li>• Your first answer is the one that counts.</li>
            <li>• The explanation appears after you submit.</li>
          </>
        ) : (
          <>
            <li>• Up to five questions, delivered one at a time.</li>
            <li>• Each question has one correct answer.</li>
            <li>
              • <span className="text-white">Your first answer counts.</span>{" "}
              Replays are practice and cannot earn XP again.
            </li>
            <li>• The explanation appears after each submission.</li>
            <li>• Questions are selected individually by the Arena server.</li>
          </>
        )}
      </ul>

      <div className="mt-6 flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.025] px-4 py-3">
        <ShieldCheck size={17} className="shrink-0 text-ice" />
        <p className="text-xs leading-relaxed text-white/50">
          Questions are revealed during gameplay. Correct answers remain
          hidden until you submit.
        </p>
      </div>

      <button
        onClick={onStart}
        disabled={loading}
        className="btn-neon mt-8 disabled:opacity-40"
        data-testid="player-start-button"
      >
        {loading ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            Preparing
          </>
        ) : (
          <>
            Start
            <ArrowRight size={16} />
          </>
        )}
      </button>
    </div>
  );
}

// --------------------------------------------------------
// QUESTION PLAYER
// --------------------------------------------------------

export default function QuestionPlayer({
  category,
  title,
  mode = "category",
  onClose,
  onScored,
}) {
  const [stage, setStage] = useState("intro");

  const [q, setQ] = useState(null);
  const [questionNumber, setQuestionNumber] = useState(0);

  const [pick, setPick] = useState(null);
  const [res, setRes] = useState(null);

  const [busy, setBusy] = useState(false);
  const [fetching, setFetching] = useState(false);

  const [loadError, setLoadError] = useState("");

  const [tally, setTally] = useState({
    correct: 0,
    xp: 0,
  });

  const isDaily = mode === "daily";
  const maxQuestions = isDaily ? 1 : 5;

  // ------------------------------------------------------
  // FETCH ONE QUESTION ONLY
  // ------------------------------------------------------

  const fetchQuestion = async (initial = false) => {
    setFetching(true);
    setLoadError("");

    try {
      let response;

      if (isDaily) {
        response = await api.get("/arena/questions/daily");
      } else {
        if (!["logic", "aptitude", "predict"].includes(category)) {
          throw new Error("Invalid question category.");
        }

        response = await api.get("/arena/questions/next", {
          params: { category },
        });
      }

      const question = response.data;

      if (
        !question?.id ||
        !Array.isArray(question.options) ||
        question.options.length < 2
      ) {
        throw new Error("The server returned an invalid question.");
      }

      setQ(question);
      setPick(null);
      setRes(null);

      if (initial) {
        setQuestionNumber(1);
        setTally({ correct: 0, xp: 0 });
      } else {
        setQuestionNumber((number) => number + 1);
      }

      setStage("play");
    } catch (error) {
      const status = error.response?.status;

      // If the participant finishes the available question pool,
      // show their results instead of a blank question.
      if (!initial && status === 404) {
        setQ(null);
        setStage("summary");
      } else {
        const message = formatErr(error);

        setLoadError(message);
        setStage("empty");
      }
    } finally {
      setFetching(false);
    }
  };

  const start = () => {
    setQ(null);
    setRes(null);
    setPick(null);
    setQuestionNumber(0);
    setTally({ correct: 0, xp: 0 });
    fetchQuestion(true);
  };

  // ------------------------------------------------------
  // MARK QUESTION AS OPENED
  // ------------------------------------------------------

  useEffect(() => {
    if (stage === "play" && q?.id) {
      api
        .post(`/arena/questions/${q.id}/open`)
        .catch((error) => {
          console.warn("Unable to register question opening:", error);
        });
    }
  }, [stage, q?.id]);

  // ------------------------------------------------------
  // SUBMIT ANSWER
  // ------------------------------------------------------

  const submit = async () => {
    if (pick === null || res || busy || !q) return;

    setBusy(true);

    try {
      const { data } = await api.post(
        `/arena/questions/${q.id}/answer`,
        { selected: pick }
      );

      setRes(data);

      const awarded = data.xp_awarded || 0;
      const awards = Array.isArray(data.awards) ? data.awards : [];

      setTally((previous) => ({
        correct: previous.correct + (data.correct ? 1 : 0),
        xp: previous.xp + awarded,
      }));

      beep(data.correct ? "good" : "bad");

      const bonusAwards = awards.filter(
        (award) => award.kind !== "question"
      );

      if (bonusAwards.length) {
        burst(true);

        bonusAwards.forEach((award) => {
          toast.success(
            `${award.reason} ${award.xp ? `+${award.xp} XP` : ""}`
          );
        });
      } else if (awarded) {
        burst(false);
      }

      if (!data.practice) {
        onScored?.();
      }
    } catch (error) {
      toast.error(formatErr(error));
    } finally {
      setBusy(false);
    }
  };

  // ------------------------------------------------------
  // NEXT QUESTION
  // ------------------------------------------------------

  const next = async () => {
    if (!res || fetching) return;

    if (isDaily || questionNumber >= maxQuestions) {
      setStage("summary");
      return;
    }

    await fetchQuestion(false);
  };

  // ------------------------------------------------------
  // KEYBOARD SHORTCUTS
  // ------------------------------------------------------

  useEffect(() => {
    const onKey = (event) => {
      if (event.key === "Escape") {
        onClose?.();
      }

      if (stage !== "play" || !q) return;

      const number = Number(event.key);

      if (!res && number >= 1 && number <= q.options.length) {
        setPick(number - 1);
      }

      if (event.key === "Enter") {
        event.preventDefault();

        if (res) {
          next();
        } else {
          submit();
        }
      }
    };

    window.addEventListener("keydown", onKey);

    return () => window.removeEventListener("keydown", onKey);
  });

  // ------------------------------------------------------
  // DISPLAY HELPERS
  // ------------------------------------------------------

  const Icon =
    CAT_ICONS?.[q?.category] ||
    CAT_ICONS?.logic ||
    CAT_ICONS?.quiz;

  const stateOf = (index) => {
    if (!res) {
      return index === pick ? "picked" : "idle";
    }

    if (index === res.correct_index) return "right";
    if (index === pick) return "wrong";

    return "idle";
  };

  // ------------------------------------------------------
  // RENDER
  // ------------------------------------------------------

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 z-[70] flex items-start justify-center overflow-y-auto bg-black/70 p-4 backdrop-blur-md sm:items-center"
      data-testid="question-player"
    >
      <motion.div
        initial={{ y: 30, scale: 0.97 }}
        animate={{ y: 0, scale: 1 }}
        className="glass-strong glow-border relative my-8 w-full max-w-2xl rounded-[2rem] p-6 sm:p-10"
      >
        <button
          onClick={onClose}
          className="absolute right-5 top-5 text-white/50 hover:text-white"
          data-testid="player-close-button"
          aria-label="Close"
        >
          <X />
        </button>

        {/* INTRO */}
        {stage === "intro" && (
          <Intro
            title={title}
            mode={mode}
            onStart={start}
            loading={fetching}
          />
        )}

        {/* LOADING */}
        {stage === "loading" && (
          <div className="py-20 text-center">
            <Loader2
              size={32}
              className="mx-auto animate-spin text-ice"
            />
            <p className="mt-4 font-mono text-xs uppercase tracking-widest text-white/50">
              Preparing your next challenge
            </p>
          </div>
        )}

        {/* QUESTION LOADING */}
        {stage === "play" && fetching && (
          <div className="py-16 text-center">
            <Loader2
              size={30}
              className="mx-auto animate-spin text-ice"
            />
            <p className="mt-4 text-sm text-white/50">
              Loading next question...
            </p>
          </div>
        )}

        {/* QUESTION */}
        {stage === "play" && !fetching && q && (
          <AnimatePresence mode="wait">
            <motion.div
              key={q.id}
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.3 }}
            >
              <div className="mb-5 flex flex-wrap items-center gap-2 pr-8">
                <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.25em] text-white/50">
                  {Icon && <Icon size={13} className="text-ice" />}
                  {q.category}
                </span>

                <span
                  className={`rounded-full border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.2em] ${
                    DIFF_STYLE?.[q.difficulty] || "border-white/20 text-white/60"
                  }`}
                >
                  {q.difficulty}
                </span>

                <span className="font-mono text-[10px] text-white/40">
                  {q.attempted ? "Practice" : `${q.xp} XP`}
                </span>

                {isDaily && (
                  <span className="rounded-full border border-neon/30 bg-neon/10 px-2 py-0.5 font-mono text-[9px] uppercase text-neon">
                    Daily +{q.bonus || 0} XP
                  </span>
                )}

                <span
                  className="ml-auto font-mono text-[10px] text-white/40"
                  data-testid="player-progress"
                >
                  {questionNumber} / {maxQuestions}
                </span>
              </div>

              <div className="mb-6 h-1 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-1 rounded-full bg-gradient-to-r from-ice via-blue-500 to-neon transition-[width] duration-500"
                  style={{
                    width: `${(questionNumber / maxQuestions) * 100}%`,
                  }}
                />
              </div>

              <h3
                className="whitespace-pre-wrap font-display text-xl font-bold leading-snug text-white sm:text-2xl"
                data-testid="question-prompt"
              >
                {q.prompt}
              </h3>

              {q.code && (
                <CodeBlock code={q.code} lang={q.code_lang} />
              )}

              <div className="mt-6 space-y-3">
                {q.options.map((option, index) => (
                  <Option
                    key={index}
                    i={index}
                    text={option}
                    state={stateOf(index)}
                    disabled={!!res || busy}
                    onClick={() => setPick(index)}
                  />
                ))}
              </div>

              {/* ANSWER FEEDBACK */}
              {res && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`mt-6 rounded-2xl border p-5 ${
                    res.correct
                      ? "border-ice/40 bg-ice/5"
                      : "border-neon/40 bg-neon/5"
                  }`}
                  data-testid="question-result"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p
                      className={`font-display text-lg font-bold uppercase tracking-wide ${
                        res.correct ? "text-ice" : "text-neon"
                      }`}
                      data-testid="question-result-verdict"
                    >
                      {res.correct ? "Correct" : "Not quite"}
                    </p>

                    <XpFlash xp={res.xp_awarded || 0} />
                  </div>

                  <p className="mt-2 text-sm leading-relaxed text-white/70">
                    {res.explanation}
                  </p>

                  {res.note && (
                    <p
                      className="mt-3 font-mono text-[10px] uppercase tracking-[0.2em] text-white/45"
                      data-testid="question-result-note"
                    >
                      {res.note}
                    </p>
                  )}
                </motion.div>
              )}

              <div className="mt-7 flex justify-end">
                {res ? (
                  <button
                    onClick={next}
                    disabled={fetching}
                    className="btn-ghost disabled:opacity-40"
                    data-testid="player-next-button"
                  >
                    {isDaily || questionNumber >= maxQuestions
                      ? "See results"
                      : "Next"}
                    <ArrowRight size={16} />
                  </button>
                ) : (
                  <button
                    onClick={submit}
                    disabled={pick === null || busy}
                    className="btn-neon disabled:opacity-40"
                    data-testid="player-submit-button"
                  >
                    {busy ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      "Submit"
                    )}
                  </button>
                )}
              </div>
            </motion.div>
          </AnimatePresence>
        )}

        {/* LOAD ERROR / EMPTY */}
        {stage === "empty" && (
          <div className="py-12 text-center">
            <p className="font-display text-xl font-bold uppercase text-white">
              Challenge unavailable
            </p>

            <p className="mt-3 text-sm leading-relaxed text-white/55">
              {loadError || "No questions are available right now."}
            </p>

            <div className="mt-7 flex flex-wrap justify-center gap-3">
              {questionNumber > 0 && (
                <button
                  onClick={() => setStage("summary")}
                  className="btn-ghost"
                >
                  View results
                </button>
              )}

              <button
                onClick={onClose}
                className="btn-neon"
              >
                Back to Arena
              </button>
            </div>
          </div>
        )}

        {/* SUMMARY */}
        {stage === "summary" && (
          <div className="text-center" data-testid="player-summary">
            <p className="eyebrow mb-3">Run complete</p>

            <p
              className="font-wordmark text-5xl font-black text-grad"
              data-testid="player-summary-xp"
            >
              +{tally.xp} XP
            </p>

            <p className="mt-3 text-white/65">
              {tally.correct} of {questionNumber} correct
            </p>

            <p className="mt-2 text-sm text-white/45">
              {isDaily
                ? "Today's Daily Challenge is complete."
                : "Every challenge counts. Every point brings you closer to victory."}
            </p>

            <button
              onClick={onClose}
              className="btn-neon mt-8"
              data-testid="player-done-button"
            >
              Back to Arena
            </button>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}

