import { BellRing, Check } from "lucide-react";
import { toast } from "sonner";
import { api, formatErr } from "@/lib/api";

export function NotificationsPanel({ notifications, onReload }) {
  const markRead = async (notice) => {
    try {
      await api.patch(`/notifications/${notice.notification_id}/read`);
      await onReload();
    } catch (error) {
      toast.error(formatErr(error));
    }
  };

  if (!notifications.length) return <p className="glass rounded-3xl p-10 text-center text-white/50" data-testid="notifications-empty">No notifications yet.</p>;
  return <div className="space-y-3" data-testid="notifications-panel">{notifications.map((notice) => <article key={notice.notification_id} className={`glass flex flex-wrap items-start justify-between gap-4 rounded-2xl p-5 ${notice.read_at ? "opacity-60" : "border-ice/40"}`} data-testid={`notification-${notice.notification_id}`}><div className="flex min-w-0 flex-1 gap-3"><BellRing size={17} className="mt-1 shrink-0 text-ice" /><div className="min-w-0 [overflow-wrap:anywhere]"><p className="font-display text-lg font-bold uppercase text-white">{notice.title}</p><p className="mt-1 text-sm text-white/60">{notice.message}</p><p className="mt-2 font-mono text-[10px] uppercase text-white/30">{new Date(notice.created_at).toLocaleString("en-IN")} · email {notice.email_status}</p></div></div>{!notice.read_at && <button onClick={() => markRead(notice)} className="btn-ghost !px-3 !py-2 !text-[10px]" data-testid={`notification-read-${notice.notification_id}`}><Check size={13} /> Mark read</button>}</article>)}</div>;
}