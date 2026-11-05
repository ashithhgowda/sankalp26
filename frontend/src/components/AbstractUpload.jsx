import { useRef, useState } from "react";
import { Download, FileText, Loader2, UploadCloud } from "lucide-react";
import { toast } from "sonner";
import { api, downloadFile, formatErr } from "@/lib/api";

const MAX = 3 * 1024 * 1024;
const OK = ["pdf"];

export default function AbstractUpload({ abstract, onUploaded, locked, topicId }) {
  const input = useRef(null);
  const [busy, setBusy] = useState(false);
  const [drag, setDrag] = useState(false);

  const send = async (file) => {
    if (!file) return;
    const ext = file.name.split(".").pop().toLowerCase();
    if (!OK.includes(ext)) return toast.error("Only PDF files are allowed");
    if (file.size > MAX) return toast.error("File is larger than 3 MB");
    if (!topicId) return toast.error("Choose a challenge topic first");
    const fd = new FormData();
    fd.append("topic_id", topicId);
    fd.append("file", file);
    setBusy(true);
    try { const { data } = await api.post("/applications/abstract", fd); onUploaded(data); toast.success("Abstract uploaded"); }
    catch (e) { toast.error(formatErr(e)); }
    finally { setBusy(false); if (input.current) input.current.value = ""; }
  };

  return (
    <div className="glass rounded-3xl p-7" data-testid="abstract-upload-card">
      <p className="eyebrow mb-4">One-page abstract</p>
      {abstract && (
        <div className="mb-4 flex items-center justify-between gap-3 rounded-2xl border border-ice/30 bg-cerulean/10 px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <FileText size={18} className="shrink-0 text-ice" />
            <div className="min-w-0">
              <p className="truncate text-sm text-white" data-testid="abstract-filename">{abstract.filename}</p>
              <p className="font-mono text-[10px] text-white/40">{(abstract.size / 1024).toFixed(0)} KB · {new Date(abstract.uploaded_at).toLocaleString()}</p>
            </div>
          </div>
          <button onClick={() => downloadFile(abstract.file_id, abstract.filename).catch((e) => toast.error(formatErr(e)))} className="text-white/60 hover:text-white" data-testid="abstract-download-button"><Download size={16} /></button>
        </div>
      )}
      {!locked && (
        <button type="button" onClick={() => input.current?.click()} disabled={busy} data-testid="abstract-upload-dropzone"
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); send(e.dataTransfer.files[0]); }}
          className={`flex w-full flex-col items-center gap-2 rounded-2xl border border-dashed px-4 py-7 text-center transition-colors ${drag ? "border-neon bg-neon/10" : "border-white/20 hover:border-ice/60"}`}>
          {busy ? <Loader2 className="animate-spin text-ice" /> : <UploadCloud className="text-ice" />}
          <span className="text-sm text-white/80">{abstract ? "Replace abstract" : "Upload abstract"}</span>
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">PDF · max 3 MB</span>
        </button>
      )}
      <input ref={input} type="file" accept=".pdf" className="hidden" onChange={(e) => send(e.target.files[0])} data-testid="abstract-file-input" />
    </div>
  );
}
