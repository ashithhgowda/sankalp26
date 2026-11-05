import { useEffect, useMemo, useState } from "react";
import { Pencil, Plus, Trash2, X } from "lucide-react";
import { toast } from "sonner";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { api, formatErr } from "@/lib/api";

const CATS = ["logic", "quiz", "debug", "predict", "trivia", "rapid"];
const SETS = ["gates", "protocols", "false"];
const BLANK = { category: "quiz", set: null, difficulty: "easy", prompt: "", code: "", code_lang: "", options: ["", "", "", ""], answer_index: 0, explanation: "", xp: "", published: true };

function QuestionForm({ initial, onSaved, onClose }) {
  const [f, setF] = useState(initial ? { ...initial, xp: initial.xp ?? "" } : BLANK);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault();
    const body = { ...f, set: f.category === "rapid" ? f.set || "gates" : null, xp: f.xp === "" ? null : Number(f.xp), answer_index: Number(f.answer_index) };
    ["id", "slug"].forEach((k) => delete body[k]);
    try {
      if (initial) await api.put(`/arena/admin/questions/${initial.id}`, body); else await api.post("/arena/admin/questions", body);
      toast.success("Challenge saved"); onSaved();
    } catch (err) { toast.error(formatErr(err)); }
  };
  return (
    <form onSubmit={save} className="space-y-4" data-testid="arena-question-form">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <label><span className="field-label">Category</span><select className="field" value={f.category} onChange={set("category")} data-testid="aq-category">{CATS.map((c) => <option key={c} className="bg-jet">{c}</option>)}</select></label>
        {f.category === "rapid" && <label><span className="field-label">Rapid set</span><select className="field" value={f.set || "gates"} onChange={set("set")} data-testid="aq-set">{SETS.map((c) => <option key={c} className="bg-jet">{c}</option>)}</select></label>}
        <label><span className="field-label">Difficulty</span><select className="field" value={f.difficulty} onChange={set("difficulty")} data-testid="aq-difficulty">{["easy", "medium", "hard"].map((c) => <option key={c} className="bg-jet">{c}</option>)}</select></label>
        <label><span className="field-label">XP (blank = auto)</span><input type="number" min="0" max="100" className="field" value={f.xp} onChange={set("xp")} data-testid="aq-xp" /></label>
      </div>
      <label className="block"><span className="field-label">Question</span><textarea required className="field min-h-[70px]" value={f.prompt} onChange={set("prompt")} data-testid="aq-prompt" /></label>
      <div className="grid grid-cols-[1fr_140px] gap-3">
        <label><span className="field-label">Code snippet (optional)</span><textarea className="field min-h-[70px] font-mono text-xs" value={f.code} onChange={set("code")} data-testid="aq-code" /></label>
        <label><span className="field-label">Language</span><input className="field" placeholder="verilog" value={f.code_lang} onChange={set("code_lang")} data-testid="aq-lang" /></label>
      </div>
      <div>
        <span className="field-label">Options · select the correct one</span>
        <div className="space-y-2">
          {f.options.map((o, i) => (
            <div key={i} className="flex items-center gap-2">
              <input type="radio" name="answer" checked={Number(f.answer_index) === i} onChange={() => setF({ ...f, answer_index: i })} data-testid={`aq-answer-${i}`} className="accent-[#ff2d95]" />
              <input required className="field !py-2" value={o} onChange={(e) => setF({ ...f, options: f.options.map((x, j) => (j === i ? e.target.value : x)) })} data-testid={`aq-option-${i}`} />
              {f.options.length > 2 && <button type="button" onClick={() => setF({ ...f, options: f.options.filter((_, j) => j !== i), answer_index: 0 })} className="text-white/40 hover:text-neon"><X size={15} /></button>}
            </div>
          ))}
        </div>
        {f.options.length < 6 && <button type="button" onClick={() => setF({ ...f, options: [...f.options, ""] })} className="mt-2 text-xs text-ice hover:underline" data-testid="aq-add-option">+ Add option</button>}
      </div>
      <label className="block"><span className="field-label">Explanation (shown after answering)</span><textarea required className="field min-h-[60px]" value={f.explanation} onChange={set("explanation")} data-testid="aq-explanation" /></label>
      <label className="flex items-center gap-3 text-sm text-white/70"><Switch checked={f.published} onCheckedChange={(v) => setF({ ...f, published: v })} data-testid="aq-published" /> Published</label>
      <div className="flex justify-end gap-3"><button type="button" onClick={onClose} className="btn-ghost">Cancel</button><button className="btn-neon" data-testid="aq-save">Save challenge</button></div>
    </form>
  );
}

export default function ArenaQuestions() {
  const [list, setList] = useState([]);
  const [cat, setCat] = useState("all");
  const [edit, setEdit] = useState(null);
  const load = () => api.get("/arena/admin/questions").then((r) => setList(r.data)).catch((e) => toast.error(formatErr(e)));
  useEffect(() => { load(); }, []);
  const shown = useMemo(() => list.filter((q) => cat === "all" || q.category === cat), [list, cat]);

  const publish = async (q, v) => { try { await api.patch(`/arena/admin/questions/${q.id}/publish`, { value: v }); load(); } catch (e) { toast.error(formatErr(e)); } };
  const remove = async (q) => { if (!window.confirm("Delete this challenge? XP already earned is kept.")) return; try { await api.delete(`/arena/admin/questions/${q.id}`); toast.success("Deleted"); load(); } catch (e) { toast.error(formatErr(e)); } };

  return (
    <div data-testid="arena-admin-questions">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <p className="eyebrow mr-auto">Challenges · {list.length}</p>
        {["all", ...CATS].map((c) => <button key={c} onClick={() => setCat(c)} className={`rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] ${cat === c ? "border-neon text-white" : "border-white/10 text-white/50"}`} data-testid={`aq-filter-${c}`}>{c}</button>)}
        <button onClick={() => setEdit("new")} className="btn-neon !px-5 !py-2.5 !text-[10px]" data-testid="aq-new-button"><Plus size={14} /> New challenge</button>
      </div>
      <div className="glass overflow-x-auto rounded-3xl">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead><tr className="border-b border-white/10 font-mono text-[10px] uppercase tracking-[0.25em] text-white/40"><th className="px-5 py-3">Challenge</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">XP</th><th className="px-4 py-3">Answer</th><th className="px-4 py-3">Live</th><th className="px-5 py-3" /></tr></thead>
          <tbody>{shown.map((q) => (
            <tr key={q.id} className="border-b border-white/5" data-testid={`aq-row-${q.slug}`}>
              <td className="max-w-[340px] px-5 py-3 text-white/80"><p className="line-clamp-2">{q.prompt}</p></td>
              <td className="px-4 py-3 font-mono text-[11px] text-white/55">{q.category}{q.set ? `/${q.set}` : ""} · {q.difficulty}</td>
              <td className="px-4 py-3 font-mono text-ice">{q.category === "rapid" ? "run" : q.xp}</td>
              <td className="max-w-[160px] truncate px-4 py-3 text-xs text-white/55">{q.options[q.answer_index]}</td>
              <td className="px-4 py-3"><Switch checked={q.published} onCheckedChange={(v) => publish(q, v)} data-testid={`aq-publish-${q.slug}`} /></td>
              <td className="px-5 py-3 text-right"><div className="flex justify-end gap-3">
                <button onClick={() => setEdit(q)} className="text-white/50 hover:text-white" data-testid={`aq-edit-${q.slug}`}><Pencil size={15} /></button>
                <button onClick={() => remove(q)} className="text-white/50 hover:text-neon" data-testid={`aq-delete-${q.slug}`}><Trash2 size={15} /></button>
              </div></td>
            </tr>))}
          </tbody>
        </table>
      </div>
      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)}>
        <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto border-white/10 bg-[#111114] text-white">
          <DialogHeader><DialogTitle className="font-display uppercase tracking-wide">{edit === "new" ? "New challenge" : "Edit challenge"}</DialogTitle></DialogHeader>
          {edit && <QuestionForm initial={edit === "new" ? null : edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); load(); }} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}
