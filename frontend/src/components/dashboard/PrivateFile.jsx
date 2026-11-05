import { useEffect, useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { api, downloadFile, formatErr } from "@/lib/api";
import { toast } from "sonner";

export function PrivateImage({ file, alt, testId }) {
  const [src, setSrc] = useState(null);
  useEffect(() => {
    let url;
    if (file?.file_id) api.get(`/files/${file.file_id}`, { responseType: "blob" }).then(({ data }) => { url = URL.createObjectURL(data); setSrc(url); }).catch(() => setSrc(false));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [file?.file_id]);
  if (!file) return null;
  if (src === false) return <p className="text-sm text-neon" data-testid={`${testId}-error`}>Preview unavailable</p>;
  if (!src) return <div className="flex aspect-square items-center justify-center border border-white/10 bg-black/20" data-testid={`${testId}-loading`}><Loader2 className="animate-spin text-ice" /></div>;
  return <img src={src} alt={alt} className="aspect-square w-full object-contain bg-white" data-testid={testId} />;
}

export function PrivateDownload({ file, label = "Download", testId }) {
  if (!file) return null;
  return <button type="button" onClick={() => downloadFile(file.file_id, file.filename).catch((error) => toast.error(formatErr(error)))} className="btn-ghost !px-4 !py-2 !text-[10px]" data-testid={testId}><Download size={14} /> {label}</button>;
}