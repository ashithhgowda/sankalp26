import { useCallback, useEffect, useState } from "react";
import { BellRing, ClipboardCheck, Clock3, FileCode2, Gauge, ListChecks, Loader2, ReceiptIndianRupee, Scale, UsersRound } from "lucide-react";
import { toast } from "sonner";
import DashShell from "@/components/DashShell";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, formatErr } from "@/lib/api";
import { ParticipantsPanel, TeamsPanel } from "@/pages/admin/PeoplePanels";
import { TopicsPanel } from "@/pages/admin/TopicsPanel";
import { ApplicationsPanel } from "@/pages/admin/ApplicationsPanel";
import { PaymentsPanel } from "@/pages/admin/PaymentsPanel";
import { TimelinePanel } from "@/pages/admin/TimelinePanel";
import { ProjectsPanel } from "@/pages/admin/ProjectsPanel";
import { JudgingPanel } from "@/pages/admin/JudgingPanel";
import { AdminNotificationsPanel } from "@/pages/admin/NotificationsPanel";

const TABS = [["overview", Gauge, "Overview"], ["people", UsersRound, "People"], ["topics", ListChecks, "Topics"], ["applications", ClipboardCheck, "Abstracts"], ["notifications", BellRing, "Notices"], ["payments", ReceiptIndianRupee, "Payments"], ["timeline", Clock3, "Timeline"], ["projects", FileCode2, "Projects"], ["judging", Scale, "Judging"]];

export default function AdminDashboard() {
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const load = useCallback(async () => {
    try {
      const [overview, teams, participants, topics, applications, notifications, payments, projects] = await Promise.all([
        api.get("/admin/overview"), api.get("/admin/teams"), api.get("/admin/participants"), api.get("/admin/topics"),
        api.get("/admin/applications"), api.get("/admin/notifications"), api.get("/admin/payments"), api.get("/admin/projects"),
      ]);
      setData({ overview: overview.data, teams: teams.data, participants: participants.data, topics: topics.data,
        applications: applications.data, notifications: notifications.data, payments: payments.data, projects: projects.data });
      setLoadError(null);
    } catch (error) {
      setLoadError(formatErr(error));
      toast.error(formatErr(error));
    }
  }, []);
  useEffect(() => { load(); }, [load]);
  const retryEmail = async (id) => { try { const { data } = await api.post(`/admin/notifications/${id}/retry`); toast.success(`Email retry ${data.email_status}`); await load(); } catch (error) { toast.error(formatErr(error)); } };
  if (!data) return <DashShell eyebrow="Admin // core control" title="Loading operations…"><div className="glass rounded-2xl p-6 text-center" role={loadError ? "alert" : undefined} data-testid="admin-dashboard-loading">{loadError ? <><p className="text-sm text-neon">{loadError}</p><button className="btn-ghost mt-4" onClick={load}>Retry loading operations</button></> : <Loader2 className="mx-auto animate-spin text-ice" />}</div></DashShell>;
  const { overview } = data;
  return <DashShell eyebrow="Admin // Phase 1 control center" title={<>Core <span className="text-grad">operations</span></>}>
    {loadError && <p className="mb-4 rounded-xl border border-neon/30 bg-neon/5 p-3 text-sm text-neon" role="alert">{loadError} <button className="ml-2 underline" onClick={load}>Retry</button></p>}
    <Tabs defaultValue={new URLSearchParams(window.location.search).get("section") || "overview"} data-testid="admin-dashboard-tabs"><TabsList className="mb-8 flex h-auto max-w-full flex-nowrap justify-start gap-1 overflow-x-auto border border-white/10 bg-white/[0.03] p-1">{TABS.map(([key, Icon, label]) => <TabsTrigger key={key} value={key} data-testid={`admin-tab-${key}`} className="shrink-0 gap-2 px-3 py-2 font-mono text-[10px] uppercase data-[state=active]:bg-neon data-[state=active]:text-white"><Icon size={13} />{label}</TabsTrigger>)}</TabsList>
    <TabsContent value="overview"><div className="grid grid-cols-2 gap-4 lg:grid-cols-4">{[["Teams", overview.teams], ["Participants", overview.participants], ["Applications", overview.applications], ["Selected", overview.selected], ["Payment reviews", overview.payments_pending], ["Confirmed", overview.confirmed], ["Projects submitted", overview.submissions]].map(([label, value]) => <article key={label} className="glass rounded-2xl p-5" data-testid={`admin-metric-${label.toLowerCase().replaceAll(" ", "-")}`}><p className="font-wordmark text-3xl font-black text-white">{value}</p><p className="mt-2 font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">{label}</p></article>)}</div><section className="glass-strong mt-6 rounded-3xl p-7"><p className="eyebrow">Phase 1 posture</p><h2 className="mt-2 font-display text-2xl font-bold uppercase text-white">Core workflows before Arena</h2><p className="mt-3 max-w-3xl text-sm leading-relaxed text-white/55">Registration, individual account activation, abstracts, manual payment verification, project submissions and two-phase judging are controlled here. Arena remains preserved and outside this Phase 1 workspace.</p></section>{overview.notifications?.length > 0 && <section className="mt-6 space-y-3" data-testid="admin-notifications">{overview.notifications.map((notice) => <article key={notice.notification_id} className="glass flex flex-wrap items-start justify-between gap-3 rounded-2xl p-5"><div><p className="font-display text-lg font-bold uppercase text-white">{notice.title}</p><p className="text-sm text-white/55">{notice.message}</p></div>{notice.email_status === "failed" && <button onClick={() => retryEmail(notice.notification_id)} className="btn-ghost !px-3 !py-2 !text-[9px]" data-testid={`admin-notification-retry-${notice.notification_id}`}>Retry email</button>}</article>)}</section>}</TabsContent>
    <TabsContent value="people"><div className="space-y-7"><TeamsPanel teams={data.teams} onReload={load} /><ParticipantsPanel rows={data.participants} /></div></TabsContent>
    <TabsContent value="topics"><TopicsPanel topics={data.topics} onReload={load} /></TabsContent>
    <TabsContent value="applications"><ApplicationsPanel applications={data.applications} topics={data.topics} onReload={load} /></TabsContent>
    <TabsContent value="notifications"><AdminNotificationsPanel notifications={data.notifications} onReload={load} /></TabsContent>
    <TabsContent value="payments"><PaymentsPanel payments={data.payments} onReload={load} /></TabsContent>
    <TabsContent value="timeline"><TimelinePanel /></TabsContent>
    <TabsContent value="projects"><ProjectsPanel projects={data.projects} onReload={load} /></TabsContent>
    <TabsContent value="judging"><JudgingPanel teams={data.teams} /></TabsContent>
  </Tabs></DashShell>;
}