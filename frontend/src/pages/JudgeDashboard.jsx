import { useCallback, useEffect, useMemo, useState } from "react";
import { ExternalLink, Loader2, Save, Send, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import DashShell from "@/components/DashShell";
import { PrivateDownload } from "@/components/dashboard/PrivateFile";
import { api, formatErr } from "@/lib/api";

export default function JudgeDashboard() {
  const [submissions, setSubmissions] = useState(null);
  const [selected, setSelected] = useState(null);
  const [phase, setPhase] = useState("phase1");
  const [criteria, setCriteria] = useState([]);
  const [scores, setScores] = useState({});
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/judge/submissions");
      setSubmissions(data);
      setSelected((current) => current ? data.find((item) => item.team_id === current.team_id) || data[0] : data[0]);
      setLoadError(null);
    } catch (error) {
      setLoadError(formatErr(error));
      toast.error(formatErr(error));
    }
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (selected && !selected.allowed_phases.includes(phase)) setPhase(selected.allowed_phases[0]); }, [selected, phase]);
  useEffect(() => {
    if (!selected || !phase) return;
    const controller = new AbortController();
    setCriteria([]); setScores({});
    api.get(`/judge/criteria/${phase}`, { signal: controller.signal }).then(({ data }) => {
      setCriteria(data);
      const prior = selected.evaluations?.find((x) => x.phase === phase);
      setScores(Object.fromEntries((prior?.scores || []).map((x) => [x.criterion_id, x.marks])));
      setComment(prior?.comment || "");
    }).catch((error) => { if (error.code !== "ERR_CANCELED") toast.error(formatErr(error)); });
    return () => controller.abort();
  }, [selected, phase]);
  const existing = useMemo(() => selected?.evaluations?.find((x) => x.phase === phase), [selected, phase]);
  const save = async (action) => { if (criteria.some((item) => scores[item.criterion_id] === "" || scores[item.criterion_id] == null)) return toast.error("Enter every criterion mark before saving"); setBusy(true); try { await api.put(`/judge/evaluations/${selected.team_id}`, { phase, scores: criteria.map((item) => ({ criterion_id: item.criterion_id, marks: Number(scores[item.criterion_id]) })), comment, action }); toast.success(action === "submit" ? "Evaluation submitted and locked" : "Draft saved"); await load(); } catch (error) { toast.error(formatErr(error)); } finally { setBusy(false); } };
  if (!submissions) return <DashShell eyebrow="Judge // assigned evaluation" title="Loading assignments…"><div className="glass rounded-2xl p-6 text-center" role={loadError ? "alert" : undefined} data-testid="judge-dashboard-loading">{loadError ? <><p className="text-sm text-neon">{loadError}</p><button className="btn-ghost mt-4" onClick={load}>Retry loading assignments</button></> : <Loader2 className="mx-auto animate-spin text-ice" />}</div></DashShell>;
  return <DashShell eyebrow="Judge // assigned evaluation" title={<>Two-phase <span className="text-grad">review</span></>}>{loadError && <p className="mb-4 rounded-xl border border-neon/30 bg-neon/5 p-3 text-sm text-neon" role="alert">{loadError} <button className="ml-2 underline" onClick={load}>Retry</button></p>}<div className="grid grid-cols-1 gap-6 lg:grid-cols-[320px_1fr]" data-testid="judge-dashboard"><aside className="glass h-fit rounded-3xl p-4"><p className="eyebrow px-2 py-3">Assigned teams</p>{submissions.length === 0 && <p className="px-2 py-6 text-sm text-white/45" data-testid="judge-no-assignments">No teams are assigned to this judge.</p>}{submissions.map((item) => <button key={item.submission_id} onClick={() => { setSelected(item); setPhase(item.allowed_phases[0]); }} className={`mb-2 w-full border p-4 text-left transition-colors ${selected?.submission_id === item.submission_id ? "border-neon bg-neon/10" : "border-white/10 bg-white/[0.02] hover:border-ice"}`} data-testid={`judge-team-${item.team_id}`}><p className="font-display text-lg font-bold uppercase text-white">{item.team?.name}</p><p className="text-xs text-white/40">{item.status} · {item.allowed_phases.join(" + ")}</p></button>)}</aside>
    {selected && <section className="space-y-6"><article className="glass-strong rounded-3xl p-7"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="eyebrow">Private assigned submission</p><h2 className="mt-2 font-display text-3xl font-bold uppercase text-white" data-testid="judge-project-title">{selected.title}</h2><p className="text-ice">{selected.team?.name}</p></div><ShieldCheck className="text-ice" /></div><p className="mt-5 text-sm leading-relaxed text-white/60">{selected.description}</p><div className="mt-5 flex flex-wrap gap-2"><a href={selected.github_url} target="_blank" rel="noreferrer" className="btn-ghost !px-4 !py-2 !text-[10px]" data-testid="judge-project-github"><ExternalLink /> GitHub</a><a href={selected.demo_url} target="_blank" rel="noreferrer" className="btn-ghost !px-4 !py-2 !text-[10px]" data-testid="judge-project-demo"><ExternalLink /> Demo</a>{selected.presentation_file && <PrivateDownload file={selected.presentation_file} label="Documentation" testId="judge-project-document" />}</div></article>
      {(selected.video_url || selected.resources?.length > 0) && <article className="glass rounded-3xl p-7" data-testid="judge-additional-deliverables"><p className="eyebrow">Additional deliverables</p><div className="mt-4 flex flex-wrap gap-2">{selected.video_url && <a href={selected.video_url} target="_blank" rel="noreferrer" className="btn-ghost !px-4 !py-2 !text-[10px]" data-testid="judge-video-link"><ExternalLink /> Video demo</a>}{selected.resources?.map((resource) => resource.file ? <PrivateDownload key={resource.resource_id} file={resource.file} label={resource.title} testId={`judge-resource-file-${resource.resource_id}`} /> : <a key={resource.resource_id} href={resource.url} target="_blank" rel="noreferrer" className="btn-ghost !px-4 !py-2 !text-[10px]" data-testid={`judge-resource-link-${resource.resource_id}`}><ExternalLink /> {resource.title}</a>)}</div></article>}
      <article className="glass rounded-3xl p-7"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="eyebrow">Independent score record</p><h3 className="mt-2 font-display text-2xl font-bold uppercase text-white">{phase === "phase1" ? "Phase 1 · Midnight" : "Phase 2 · Final"}</h3></div><select className="field !w-auto" value={phase} onChange={(e) => setPhase(e.target.value)} data-testid="judge-phase-select">{selected.allowed_phases.map((item) => <option key={item} value={item}>{item === "phase1" ? "Phase 1 · Midnight" : "Phase 2 · Final"}</option>)}</select></div>{existing?.status === "submitted" && <p className="mt-5 border-l-2 border-ice pl-3 text-sm text-ice" data-testid="judge-evaluation-locked">This evaluation was submitted and is locked.</p>}{criteria.length === 0 && <p className="mt-5 text-neon" data-testid="judge-no-criteria">The administrator has not configured active criteria for this phase.</p>}<div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">{criteria.map((criterion) => <label key={criterion.criterion_id}><span className="field-label">{criterion.title} · max {criterion.max_marks} · weight {criterion.weight}</span><input className="field" type="number" min="0" max={criterion.max_marks} step="0.1" required disabled={existing?.status === "submitted"} value={scores[criterion.criterion_id] ?? ""} onChange={(e) => setScores({ ...scores, [criterion.criterion_id]: e.target.value })} data-testid={`judge-score-${criterion.criterion_id}`} /></label>)}</div><textarea className="field mt-4 min-h-[110px]" disabled={existing?.status === "submitted"} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Judge comments" data-testid="judge-comment-input" />{existing?.status !== "submitted" && criteria.length > 0 && <div className="mt-5 flex gap-3"><button onClick={() => save("save")} disabled={busy} className="btn-ghost" data-testid="judge-save-draft-button"><Save /> Save draft</button><button onClick={() => save("submit")} disabled={busy} className="btn-neon" data-testid="judge-submit-evaluation-button">{busy ? <Loader2 className="animate-spin" /> : <><Send /> Submit and lock</>}</button></div>}</article>
    </section>}</div></DashShell>;
}