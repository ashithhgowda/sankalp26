import { useState } from "react";
import { FileText, Plus, Search } from "lucide-react";
import { toast } from "sonner";
import { api, downloadFile, formatErr } from "@/lib/api";
import { DateTimeISTField } from "@/components/DateTimeISTField";

const EMPTY = { team_name: "", college: "", leader_name: "", contact_email: "", topic_id: "", submission_date: "", notes: "", status: "pending" };

export function ApplicationsPanel({ applications, topics, onReload }) {
  const [query, setQuery] = useState("");
  const [manual, setManual] = useState(EMPTY);
  const [notes, setNotes] = useState({});
  const filtered = applications.filter((item) => `${item.application_id} ${item.team?.name || item.team_name || ""} ${item.leader_name || ""} ${item.topic_title}`.toLowerCase().includes(query.toLowerCase()));
  const create = async (event) => {
    event.preventDefault();
    if (!manual.submission_date) return toast.error("Choose the submission date");
    try { await api.post("/admin/applications/manual", manual); toast.success("Email submission recorded"); setManual(EMPTY); onReload(); }
    catch (error) { toast.error(formatErr(error)); }
  };
  const review = async (item, status) => {
    try {
      const { data } = await api.patch(`/admin/applications/${item.application_id}`, { status, admin_notes: notes[item.application_id] ?? item.admin_notes ?? "" });
      toast.success(`Application marked ${status.replaceAll("_", " ")} · email ${data.email_status}`); onReload();
    } catch (error) { toast.error(formatErr(error)); }
  };
  return <div className="space-y-7" data-testid="admin-applications-panel">
    <form onSubmit={create} className="glass-strong rounded-3xl p-6" data-testid="admin-manual-application-form">
      <div className="mb-5 flex items-center gap-2"><Plus className="text-ice" /><p className="eyebrow">Record manual email submission</p></div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <input className="field" required value={manual.team_name} onChange={(e) => setManual({ ...manual, team_name: e.target.value })} placeholder="Team name" data-testid="manual-application-team-input" />
        <input className="field" required value={manual.college} onChange={(e) => setManual({ ...manual, college: e.target.value })} placeholder="College" data-testid="manual-application-college-input" />
        <input className="field" required value={manual.leader_name} onChange={(e) => setManual({ ...manual, leader_name: e.target.value })} placeholder="Team leader" data-testid="manual-application-leader-input" />
        <input className="field" type="email" required value={manual.contact_email} onChange={(e) => setManual({ ...manual, contact_email: e.target.value })} placeholder="Contact email" data-testid="manual-application-email-input" />
        <select className="field" required value={manual.topic_id} onChange={(e) => setManual({ ...manual, topic_id: e.target.value })} data-testid="manual-application-topic-select"><option value="">Challenge topic</option>{topics.map((topic) => <option key={topic.topic_id} value={topic.topic_id}>{topic.title}</option>)}</select>
        <DateTimeISTField value={manual.submission_date} onChange={(value) => setManual({ ...manual, submission_date: value })} testId="manual-application-date-input" placeholder="Submission date · IST" />
      </div>
      <textarea className="field mt-3" value={manual.notes} onChange={(e) => setManual({ ...manual, notes: e.target.value })} placeholder="Administrative notes" data-testid="manual-application-notes-input" />
      <button className="btn-neon mt-4" data-testid="manual-application-submit-button">Record application</button>
    </form>
    <label className="relative block"><Search className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30" size={16} /><input className="field !pl-11" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search team, leader, topic or submission ID" data-testid="admin-applications-search" /></label>
    <div className="space-y-4">{filtered.map((item) => <article key={item.application_id} className="glass rounded-3xl p-6" data-testid={`admin-application-${item.application_id}`}>
      <div className="flex flex-wrap items-start justify-between gap-4"><div><p className="font-display text-xl font-bold uppercase text-white">{item.team?.name || item.team_name}</p><p className="text-xs text-white/40">{item.application_id} · {item.method} · {item.topic_title}</p></div><span className="font-mono text-xs uppercase text-neon" data-testid={`admin-application-status-${item.application_id}`}>{item.status?.replaceAll("_", " ")}</span></div>
      {item.memberships?.length > 0 && <p className="mt-3 text-sm text-white/55">Members: {item.memberships.map((member) => `${member.name} (${member.usn})`).join(", ")}</p>}
      <div className="mt-5 flex flex-wrap gap-2">{item.file && <button onClick={() => downloadFile(item.file.file_id, item.file.filename).catch((error) => toast.error(formatErr(error)))} className="btn-ghost !px-4 !py-2 !text-[10px]" data-testid={`admin-application-download-${item.application_id}`}><FileText /> Download PDF</button>}{["pending", "under_review", "selected", "rejected"].map((status) => <button key={status} onClick={() => review(item, status)} className={`btn-ghost !px-4 !py-2 !text-[10px] ${item.status === status ? "!border-neon text-neon" : ""}`} data-testid={`admin-application-${status}-${item.application_id}`}>{status.replaceAll("_", " ")}</button>)}</div>
      <textarea className="field mt-4" value={notes[item.application_id] ?? item.admin_notes ?? ""} onChange={(e) => setNotes({ ...notes, [item.application_id]: e.target.value })} placeholder="Administrative review notes" data-testid={`admin-application-notes-${item.application_id}`} />
    </article>)}</div>
  </div>;
}