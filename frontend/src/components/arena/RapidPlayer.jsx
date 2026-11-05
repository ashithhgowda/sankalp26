import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Check, Loader2, Timer, X } from "lucide-react";
import { toast } from "sonner";
import { api, formatErr } from "@/lib/api";
import { beep, burst } from "@/lib/arenaFx";
import { CodeBlock, Option, XpFlash } from "@/components/arena/QuestionPlayer";

export default function RapidPlayer({ set, used, onClose, onScored }) {
  const [stage, setStage] = useState("intro");
  const [run, setRun] = useState(null);
  const [i, setI] = useState(0);
  const [answers, setAnswers] = useState([]);
  const [left, setLeft] = useState(60);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [wasUsed, setWasUsed] = useState(used);
  const deadline = useRef(0);
  const sent = useRef(false);

  const start = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/arena/rapid/start", { set: set.key });
      setRun(data); setAnswers(Array(data.questions.length).fill(null)); setI(0);
      deadline.current = Date.now() + data.seconds * 1000; setLeft(data.seconds); sent.current = false;
      setStage("play");
    } catch (e) { toast.error(formatErr(e)); }
    finally { setBusy(false); }
  };

  const submit = useCallback(async (final) => {
    if (sent.current) return;
    sent.current = true;
    setStage("submitting");
    try {
      const { data } = await api.post(`/arena/rapid/${run.run_id}/submit`, { answers: final });
      setResult(data); setStage("result");
      beep(data.correct >= 4 ? "win" : "good");
      if (data.xp_awarded) burst(data.correct === 5);
      setWasUsed(true);
      onScored?.();
    } catch (e) { toast.error(formatErr(e)); setStage("result"); }
  }, [run, onScored]);

  useEffect(() => {
    if (stage !== "play") return;
    const t = setInterval(() => {
      const s = Math.max(0, Math.ceil((deadline.current - Date.now()) / 1000));
      setLeft(s);
      if (s <= 10 && s > 0) beep("tick");
      if (s === 0) setAnswers((a) => { submit(a); return a; });
    }, 1000);
    return () => clearInterval(t);
  }, [stage, submit]);

  const choose = (k) => {
    const a = answers.map((x, j) => (j === i ? k : x));
    setAnswers(a);
    if (i + 1 >= run.questions.length) submit(a);
    else setTimeout(() => setI(i + 1), 180);
  };

  const q = run?.questions[i];

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="fixed inset-0 z-[70] flex items-start justify-center overflow-y-auto bg-black/70 p-4 backdrop-blur-md sm:items-center" data-testid="rapid-player">
      <div className="glass-strong glow-border relative my-8 w-full max-w-2xl rounded-[2rem] p-7 sm:p-10">
        <button onClick={onClose} className="absolute right-5 top-5 text-white/50 hover:text-white" data-testid="rapid-close-button" aria-label="Close"><X /></button>
        {stage === "intro" && (
          <div data-testid="rapid-intro">
            <p className="eyebrow mb-3">Rapid fire</p>
            <h2 className="font-editorial text-3xl font-extrabold uppercase text-white">{set.name}</h2>
            <p className="mt-2 text-white/55">{set.desc}</p>
            <ul className="mt-6 space-y-3 text-sm text-white/65">
              <li>• 5 questions, 60 seconds. Picking an option jumps to the next question.</li>
              <li>• 8 XP per correct answer, plus a small time bonus (up to 10 XP) if you get 4 or more right. Max 50 XP.</li>
              <li>• <span className="text-neon">{wasUsed ? "You've already used your scored run for this set — this one is practice." : "Only your FIRST run in this set scores. Make it count."}</span></li>
            </ul>
            <button onClick={start} disabled={busy} className="btn-neon mt-8" data-testid="rapid-start-button">{busy ? <Loader2 className="animate-spin" size={16} /> : <>Start the clock <ArrowRight size={16} /></>}</button>
          </div>
        )}
        {stage === "play" && q && (
          <div>
            <div className="mb-6 flex items-center justify-between pr-8">
              <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-white/50">Q {i + 1} / {run.questions.length}</span>
              <span className={`flex items-center gap-2 font-wordmark text-2xl font-black tabular-nums ${left <= 10 ? "text-neon" : "text-white"}`} data-testid="rapid-timer"><Timer size={18} />{left}s</span>
            </div>
            <div className="mb-6 h-1 rounded-full bg-white/10"><div className="h-1 rounded-full bg-gradient-to-r from-ice to-neon transition-[width] duration-1000 ease-linear" style={{ width: `${(left / run.seconds) * 100}%` }} /></div>
            <AnimatePresence mode="wait">
              <motion.div key={i} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }} transition={{ duration: 0.18 }}>
                <h3 className="font-display text-2xl font-bold text-white" data-testid="rapid-prompt">{q.prompt}</h3>
                {q.code && <CodeBlock code={q.code} />}
                <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {q.options.map((o, k) => <Option key={k} i={k} text={o} state={answers[i] === k ? "picked" : "idle"} onClick={() => choose(k)} />)}
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        )}
        {stage === "submitting" && <div className="flex justify-center py-16"><Loader2 className="animate-spin text-ice" /></div>}
        {stage === "result" && result && (
          <div data-testid="rapid-result">
            <div className="text-center">
              <p className="eyebrow mb-3">Time's up</p>
              <p className="font-wordmark text-5xl font-black text-white" data-testid="rapid-result-score">{result.correct}/5</p>
              <div className="mt-2 flex justify-center"><XpFlash xp={result.xp_awarded} /></div>
              {result.note && <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.2em] text-white/45" data-testid="rapid-result-note">{result.note}</p>}
            </div>
            <div className="mt-6 space-y-2">
              {result.results.map((r, k) => (
                <div key={k} className={`rounded-2xl border p-4 ${r.correct ? "border-ice/30" : "border-neon/30"}`}>
                  <p className="flex items-start gap-2 text-sm text-white">{r.correct ? <Check size={16} className="mt-0.5 shrink-0 text-ice" /> : <X size={16} className="mt-0.5 shrink-0 text-neon" />}{r.prompt}</p>
                  <p className="mt-1 pl-6 text-xs text-white/50">Answer: {run.questions[k].options[r.correct_index]} — {r.explanation}</p>
                </div>
              ))}
            </div>
            <div className="mt-7 flex justify-center gap-3">
              <button onClick={() => { setStage("intro"); setResult(null); }} className="btn-ghost" data-testid="rapid-practice-again">Practice again</button>
              <button onClick={onClose} className="btn-neon" data-testid="rapid-done-button">Done</button>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
