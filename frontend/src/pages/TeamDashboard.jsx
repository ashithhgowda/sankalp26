import { useCallback, useEffect, useState } from "react";
import { BellRing, FileText, LayoutDashboard, Loader2, ReceiptIndianRupee, Rocket } from "lucide-react";
import { toast } from "sonner";
import DashShell from "@/components/DashShell";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useAuth } from "@/context/AuthContext";
import { usePublicConfig } from "@/context/PublicConfigContext";
import { api, formatErr } from "@/lib/api";
import { TeamOverview } from "@/components/dashboard/TeamOverview";
import { AbstractPanel } from "@/components/dashboard/AbstractPanel";
import { PaymentPanel } from "@/components/dashboard/PaymentPanel";
import { ProjectPanel } from "@/components/dashboard/ProjectPanel";
import { NotificationsPanel } from "@/components/dashboard/NotificationsPanel";

const TABS = [["overview", LayoutDashboard, "Team"], ["abstract", FileText, "Abstract"], ["payment", ReceiptIndianRupee, "Payment"], ["project", Rocket, "Project"], ["notifications", BellRing, "Updates"]];

export default function TeamDashboard() {
  const { user } = useAuth();
  const { topics, portals } = usePublicConfig();
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const load = useCallback(async () => {
    try {
      const { data: dashboard } = await api.get("/participant/dashboard");
      setData(dashboard);
      setLoadError(null);
    } catch (error) {
      setLoadError(formatErr(error));
      toast.error(formatErr(error));
    }
  }, []);
  useEffect(() => { load(); }, [load]);
  if (!data) return <DashShell eyebrow="Participant console" title="Loading team workspace…"><div className="glass rounded-2xl p-6 text-center" role={loadError ? "alert" : undefined} data-testid="participant-dashboard-loading">{loadError ? <><p className="text-sm text-neon">{loadError}</p><button className="btn-ghost mt-4" onClick={load}>Retry loading workspace</button></> : <Loader2 className="mx-auto animate-spin text-ice" />}</div></DashShell>;
  const unreadCount = data.notifications.filter((notice) => !notice.read_at).length;
  return <DashShell eyebrow="Participant // core workspace" title={<>Team <span className="text-grad">{data.team.name}</span></>}>
    {loadError && <p className="mb-4 rounded-xl border border-neon/30 bg-neon/5 p-3 text-sm text-neon" role="alert">{loadError} <button className="ml-2 underline" onClick={load}>Retry</button></p>}
    <Tabs defaultValue={new URLSearchParams(window.location.search).get("section") || "overview"} data-testid="participant-dashboard-tabs">
    <TabsList className="mb-8 flex h-auto max-w-full flex-nowrap justify-start gap-1 overflow-x-auto border border-white/10 bg-white/[0.03] p-1">{TABS.map(([key, Icon, label]) => <TabsTrigger key={key} value={key} data-testid={`participant-tab-${key}`} className="shrink-0 gap-2 px-4 py-2 font-mono text-[10px] uppercase data-[state=active]:bg-neon data-[state=active]:text-white"><Icon size={14} />{label}{key === "notifications" && unreadCount > 0 && <span className="ml-1 rounded-full bg-neon px-1.5 py-0.5 text-[9px] leading-none text-white" aria-label={`${unreadCount} unread notifications`}>{unreadCount}</span>}</TabsTrigger>)}</TabsList>
    <TabsContent value="overview"><TeamOverview team={data.team} memberships={data.memberships} leader={user.role === "team"} onReload={load} /></TabsContent>
    <TabsContent value="abstract"><AbstractPanel application={data.application} topics={topics} leader={user.role === "team"} onReload={load} /></TabsContent>
    <TabsContent value="payment"><PaymentPanel application={data.application} payment={data.payment} settings={data.payment_settings} team={data.team} leader={user.role === "team"} onReload={load} /></TabsContent>
    <TabsContent value="project"><ProjectPanel project={data.project} eligible={data.team.registration_status === "registration_confirmed"} portalOpen={portals.project !== false} canEdit={["team", "member"].includes(user.role)} onReload={load} /></TabsContent>
    <TabsContent value="notifications"><NotificationsPanel notifications={data.notifications} onReload={load} /></TabsContent>
  </Tabs></DashShell>;
}