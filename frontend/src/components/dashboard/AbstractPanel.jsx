import { useRef, useState } from "react";
import { FileText, Loader2, Mail, UploadCloud } from "lucide-react";
import { toast } from "sonner";
import { api, formatErr } from "@/lib/api";

export function AbstractPanel({ application, topics, leader, onReload }) {
  const [topicId, setTopicId] = useState(application?.topic_id || "");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const input = useRef(null);
  const submit = async (event) => {
    event.preventDefault();
    if (!file || !topicId) return toast.error("Choose a topic and PDF");
    const data = new FormData(); data.append("topic_id", topicId); data.append("file", file);
    setBusy(true);
    try { await api.post("/applications/abstract", data); toast.success("Abstract submitted securely"); onReload(); }
    catch (error) { toast.error(formatErr(error)); } finally { setBusy(false); }
  };
  return <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.3fr_.7fr]" data-testid="abstract-panel">
    <section className="glass-strong rounded-3xl p-7"><p className="eyebrow">Website PDF submission</p><h2 className="mt-2 font-display text-2xl font-bold uppercase text-white">Abstract application</h2>
      {application && <div className="mt-5 border-l-2 border-ice pl-4" data-testid="abstract-current-status"><p className="font-mono text-xs uppercase text-ice">{application.status?.replaceAll("_", " ")}</p><p className="mt-1 text-sm text-white">{application.application_id}</p><p className="text-xs text-white/40">Submitted {new Date(application.submitted_at).toLocaleString("en-IN")}</p></div>}
      {leader && <form onSubmit={submit} className="mt-7 space-y-4" data-testid="abstract-submit-form"><label><span className="field-label">Challenge topic</span><select className="field field-select" value={topicId} onChange={(e) => setTopicId(e.target.value)} required data-testid="abstract-topic-select"><option value="">Choose one topic</option>{topics.map((topic) => <option key={topic.topic_id} value={topic.topic_id}>{topic.title}</option>)}</select></label><button type="button" className="flex w-full items-center justify-center gap-3 border border-dashed border-white/20 px-5 py-7 text-sm text-white/70 hover:border-ice" onClick={() => input.current?.click()} data-testid="abstract-file-picker"><UploadCloud className="text-ice" />{file?.name || "Choose PDF · maximum 3 MB"}</button><input ref={input} className="hidden" type="file" accept="application/pdf,.pdf" onChange={(e) => setFile(e.target.files[0])} data-testid="abstract-file-input" /><button className="btn-neon" disabled={busy} data-testid="abstract-submit-button">{busy ? <Loader2 className="animate-spin" /> : <><FileText /> {application ? "Replace and resubmit" : "Submit abstract"}</>}</button></form>}
    </section>
    <aside className="glass rounded-3xl p-7"><Mail className="text-neon" /><p className="eyebrow mt-5">Manual email method</p><h3 className="mt-2 font-display text-xl font-bold uppercase text-white">Prefer email?</h3><p className="mt-3 text-sm leading-relaxed text-white/55">Send the abstract manually to the official hackathon inbox. The administrator will record and manage that application.</p><a href="mailto:hackathon@ajiet.edu.in" className="btn-ghost mt-6 !px-4 !text-xs" data-testid="abstract-email-link">hackathon@ajiet.edu.in</a></aside>
  </div>;
}