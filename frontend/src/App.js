import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth, homeFor } from "@/context/AuthContext";
import Landing from "@/pages/Landing";
import AuthPage from "@/pages/AuthPage";
import TeamDashboard from "@/pages/TeamDashboard";
import JudgeDashboard from "@/pages/JudgeDashboard";
import AdminDashboard from "@/pages/AdminDashboard";
import LeaderboardPage from "@/pages/LeaderboardPage";
import ArenaHome from "@/pages/arena/ArenaHome";
import ArenaPlay from "@/pages/arena/ArenaPlay";
import ArenaLeaderboard from "@/pages/arena/ArenaLeaderboard";
import WinnerReveal from "@/pages/WinnerReveal";
import ActivateAccount from "@/pages/ActivateAccount";
import AccountSecurity from "@/pages/AccountSecurity";
import PasswordRecovery from "@/pages/PasswordRecovery";
import { PublicConfigProvider } from "@/context/PublicConfigContext";

const Loader = () => (
  <div className="flex min-h-screen items-center justify-center bg-jet font-mono text-[11px] uppercase tracking-[0.3em] text-ice" data-testid="app-loader">Syncing…</div>
);

function Protected({ roles, children }) {
  const { user } = useAuth();
  if (user === null) return <Loader />;
  if (!user) return <Navigate to="/auth?mode=login" replace />;
  if (!roles.includes(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return children;
}

function AuthRoute() {
  const { user } = useAuth();
  if (user === null) return <Loader />;
  if (user) return <Navigate to={homeFor(user.role)} replace />;
  return <AuthPage />;
}

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <PublicConfigProvider><BrowserRouter>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/auth" element={<AuthRoute />} />
            <Route path="/leaderboard" element={<LeaderboardPage />} />
            <Route path="/dashboard" element={<Protected roles={["team", "member"]}><TeamDashboard /></Protected>} />
            <Route path="/judge" element={<Protected roles={["judge", "admin"]}><JudgeDashboard /></Protected>} />
            <Route path="/admin" element={<Protected roles={["admin"]}><AdminDashboard /></Protected>} />
            <Route path="/arena" element={<ArenaHome />} />
            <Route path="/arena/play" element={<ArenaPlay />} />
            <Route path="/arena/leaderboard" element={<ArenaLeaderboard />} />
            <Route path="/reveal" element={<Protected roles={["admin"]}><WinnerReveal /></Protected>} />
            <Route path="/activate" element={<ActivateAccount />} />
            <Route path="/forgot-password" element={<PasswordRecovery mode="forgot" />} />
            <Route path="/reset-password" element={<PasswordRecovery mode="reset" />} />
            <Route path="/account/security" element={<AccountSecurity />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter></PublicConfigProvider>
        <Toaster theme="dark" position="bottom-right" toastOptions={{ style: { background: "rgba(18,18,20,.9)", border: "1px solid rgba(255,255,255,.12)", backdropFilter: "blur(20px)", color: "#fff" } }} />
      </AuthProvider>
    </div>
  );
}

export default App;
