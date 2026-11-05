import { useEffect, useState } from "react";
import { Clock3, Save } from "lucide-react";
import { toast } from "sonner";
import { api, formatErr } from "@/lib/api";
import { DateTimeISTField } from "@/components/DateTimeISTField";

const FIELDS = [["application_open", "Application opens"], ["application_close", "Application closes"], ["abstract_deadline", "Abstract deadline"], ["selection_announcement", "Selection announcement"], ["payment_deadline", "Payment deadline"], ["hackathon_start", "Hackathon starts"], ["hackathon_end", "Hackathon ends"], ["project_open", "Project portal opens"], ["project_close", "Project portal closes"]];
export function TimelinePanel() {
  const [form, setForm] = useState(null);
  useEffect(() => { api.get("/admin/timeline").then(({ data }) => setForm(data)).catch((error) => toast.error(formatErr(error))); }, []);
  const save = async (event) => { event.preventDefault(); try { const { data } = await api.put("/admin/timeline", form); setForm(data); toast.success("Timeline and portal controls saved in IST"); } catch (error) { toast.error(formatErr(error)); } };
  if (!form) return <p className="text-white/50">Loading timeline…</p>;
  return <form onSubmit={save} className="glass-strong rounded-3xl p-7" data-testid="admin-timeline-form"><div className="flex items-center gap-2"><Clock3 className="text-ice" /><p className="eyebrow">Event timeline · Asia/Kolkata</p></div><div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">{FIELDS.map(([key, label]) => <label key={key}><span className="field-label">{label}</span><DateTimeISTField value={form[key]} onChange={(value) => setForm((previous) => ({ ...previous, [key]: value || null }))} testId={`admin-timeline-${key}`} /></label>)}</div><div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">{["application", "abstract", "project"].map((portal) => <label key={portal}><span className="field-label">{portal} portal</span><select className="field" value={form[`${portal}_override`]} onChange={(e) => setForm((previous) => ({ ...previous, [`${portal}_override`]: e.target.value }))} data-testid={`admin-${portal}-portal-control`}><option value="auto">Automatic by dates</option><option value="open">Force open</option><option value="closed">Force closed</option></select></label>)}</div><button className="btn-neon mt-6" data-testid="admin-timeline-save"><Save /> Save timeline</button></form>;
}