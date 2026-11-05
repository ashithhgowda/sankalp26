import { useState } from "react";
import { ChevronDown, ChevronUp, Pencil, Plus, Save, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import { api, formatErr } from "@/lib/api";
import { Switch } from "@/components/ui/switch";
import { usePublicConfig } from "@/context/PublicConfigContext";

const EMPTY = { title: "", short: "", description: "", enabled: true };

export function TopicsPanel({ topics, onReload }) {
  const { refresh } = usePublicConfig();
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const submit = async (event) => {
    event.preventDefault();
    try { editing ? await api.put(`/admin/topics/${editing}`, form) : await api.post("/admin/topics", form); toast.success(editing ? "Topic updated" : "Topic added"); setEditing(null); setForm(EMPTY); await Promise.all([onReload(), refresh()]); }
    catch (error) { toast.error(formatErr(error)); }
  };
  const edit = (topic) => { setEditing(topic.topic_id); setForm({ title: topic.title, short: topic.short || "", description: topic.description, enabled: topic.enabled }); };
  const remove = async (id) => { if (!window.confirm("Delete this unused topic?")) return; try { await api.delete(`/admin/topics/${id}`); await Promise.all([onReload(), refresh()]); } catch (error) { toast.error(formatErr(error)); } };
  const move = async (index, direction) => {
    const next = [...topics]; const target = index + direction;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    try { await api.put("/admin/topics/order", { topic_ids: next.map((item) => item.topic_id) }); await Promise.all([onReload(), refresh()]); }
    catch (error) { toast.error(formatErr(error)); }
  };
  return <div className="grid grid-cols-1 gap-6 lg:grid-cols-[380px_1fr]" data-testid="admin-topics-panel">
    <form onSubmit={submit} className="glass-strong h-fit space-y-4 rounded-3xl p-6" data-testid="admin-topic-form"><p className="eyebrow">{editing ? "Edit topic" : "Add topic"}</p><input className="field" required minLength={5} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Official challenge title" data-testid="admin-topic-title-input" /><input className="field" value={form.short} onChange={(e) => setForm({ ...form, short: e.target.value })} placeholder="Short label" data-testid="admin-topic-short-input" /><textarea className="field min-h-[140px]" required minLength={10} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="Displayed description" data-testid="admin-topic-description-input" /><label className="flex items-center justify-between text-sm text-white/60">Enabled <Switch checked={form.enabled} onCheckedChange={(value) => setForm({ ...form, enabled: value })} data-testid="admin-topic-enabled-switch" /></label><button className="btn-neon w-full" data-testid="admin-topic-save-button">{editing ? <><Save /> Save topic</> : <><Plus /> Add topic</>}</button>{editing && <button type="button" onClick={() => { setEditing(null); setForm(EMPTY); }} className="btn-ghost w-full" data-testid="admin-topic-cancel-button"><X /> Cancel</button>}</form>
    <div className="space-y-3">{topics.map((topic, index) => <article key={topic.topic_id} className="glass rounded-2xl p-5" data-testid={`admin-topic-${topic.topic_id}`}><div className="flex flex-wrap items-start justify-between gap-4"><div className="min-w-0 flex-1"><p className="font-display text-lg font-bold uppercase text-white">{topic.title}</p><p className="mt-2 text-sm text-white/50">{topic.description}</p><p className={`mt-3 font-mono text-[10px] uppercase ${topic.enabled ? "text-ice" : "text-white/30"}`}>#{index + 1} · {topic.enabled ? "Enabled" : "Disabled"}</p></div><div className="flex flex-wrap gap-2"><button onClick={() => move(index, -1)} disabled={index === 0} className="btn-ghost !px-3 !py-2" data-testid={`admin-topic-up-${topic.topic_id}`}><ChevronUp /></button><button onClick={() => move(index, 1)} disabled={index === topics.length - 1} className="btn-ghost !px-3 !py-2" data-testid={`admin-topic-down-${topic.topic_id}`}><ChevronDown /></button><button onClick={() => edit(topic)} className="btn-ghost !px-3 !py-2" data-testid={`admin-topic-edit-${topic.topic_id}`}><Pencil /></button><button onClick={() => remove(topic.topic_id)} className="btn-ghost !px-3 !py-2 text-neon" data-testid={`admin-topic-delete-${topic.topic_id}`}><Trash2 /></button></div></div></article>)}</div>
  </div>;
}