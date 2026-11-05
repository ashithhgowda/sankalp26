import { Link, NavLink, useNavigate } from "react-router-dom";
import { LogOut, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { Wordmark } from "@/components/Wordmark";
import { useAuth } from "@/context/AuthContext";
import { formatErr } from "@/lib/api";

const NAV = {
  team: [["/dashboard", "Core portal"], ["/arena", "Arena"], ["/leaderboard", "Leaderboard"]],
  member: [["/dashboard", "Team status"], ["/arena", "Arena"], ["/leaderboard", "Leaderboard"]],
  judge: [["/judge", "Evaluate"], ["/leaderboard", "Leaderboard"]],
  admin: [["/admin", "Control center"], ["/judge", "Evaluate"], ["/leaderboard", "Leaderboard"], ["/arena", "Arena"], ["/reveal", "Reveal"]],
};

export default function DashShell({ title, eyebrow, children, actions }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const links = user ? NAV[user.role] : [["/", "Home"], ["/arena", "Arena"], ["/leaderboard", "Leaderboard"]];
  const signOut = async () => {
    try {
      await logout();
      nav("/");
    } catch (error) {
      toast.error(formatErr(error));
    }
  };

  return (
    <div className="grain relative min-h-screen bg-jet" data-testid="dash-shell">
      <div className="cyber-grid pointer-events-none fixed inset-0 opacity-30" />
      <div className="pointer-events-none fixed -left-40 top-0 h-[500px] w-[500px] rounded-full bg-cerulean/15 blur-[150px]" />
      <div className="pointer-events-none fixed -right-40 bottom-0 h-[500px] w-[500px] rounded-full bg-neon/10 blur-[150px]" />
      <header className="sticky top-0 z-40 px-4 pt-4 sm:px-6">
        <div className="glass-strong mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 rounded-2xl px-4 py-3 sm:rounded-full sm:px-7">
          <Link to="/" data-testid="dash-logo-link"><Wordmark className="text-lg" testid="dash-wordmark" /></Link>
          <nav className="order-3 flex w-full flex-wrap items-center gap-1 sm:order-none sm:w-auto">
            {links.map(([to, l]) => (
              <NavLink key={to} to={to} end data-testid={`dash-nav-${l.toLowerCase().replace(/\s/g, "-")}`}
                className={({ isActive }) => `rounded-full px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.22em] transition-colors sm:px-4 sm:py-2 ${isActive ? "bg-white/10 text-white" : "text-white/50 hover:text-white"}`}>{l}</NavLink>
            ))}
          </nav>
          {user ? (
            <div className="flex items-center gap-2 sm:gap-3">
              <span className="hidden rounded-full border border-neon/40 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.25em] text-neon sm:inline" data-testid="dash-role-badge">{user.role}</span>
              <Link to="/account/security" className="flex items-center gap-1 font-mono text-[10px] uppercase text-white/50 hover:text-ice" data-testid="dash-security-link"><ShieldCheck size={14} /><span className="hidden sm:inline">Security</span></Link>
              <button onClick={signOut} data-testid="dash-logout-button" className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.22em] text-white/60 hover:text-white"><LogOut size={14} /> Exit</button>
            </div>
          ) : (
            <Link to="/auth?mode=login" className="font-mono text-[10px] uppercase tracking-[0.22em] text-white/60 hover:text-white" data-testid="dash-login-link">Login</Link>
          )}
        </div>
      </header>
      <main className="relative mx-auto max-w-7xl px-5 pb-20 pt-12 sm:px-8">
        <div className="mb-10 flex flex-wrap items-end justify-between gap-6">
          <div className="min-w-0 max-w-full">
            <p className="eyebrow mb-3">{eyebrow}</p>
            <h1 className="max-w-full font-editorial text-3xl font-extrabold uppercase leading-tight text-white [overflow-wrap:anywhere] sm:text-4xl lg:text-5xl" data-testid="dash-title">{title}</h1>
          </div>
          {actions}
        </div>
        {children}
      </main>
    </div>
  );
}
