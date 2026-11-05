import "@/App.css";
import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
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

const SITE_URL = "https://www.sankalp26.in";
const ROUTE_METADATA = {
  "/": {
    title: "Sankalp26 | National Level Hackathon",
    description: "Sankalp26 is IEEE AJIET Student Branch’s national-level 24-hour hackathon in Mangaluru, India. Build solutions across six challenge tracks; compete for a ₹75,000 prize pool on 27–28 November 2026.",
    index: true,
  },
  "/leaderboard": {
    title: "Project Leaderboard | Sankalp26",
    description: "Follow project rankings from the Sankalp26 national-level hackathon.",
    index: true,
  },
  "/arena": {
    title: "Sankalp26 Arena | Play, Solve, Dominate",
    description: "Explore the Sankalp26 Arena, with puzzles, quizzes, debugging challenges, and a public participant leaderboard.",
    index: true,
  },
  "/arena/leaderboard": {
    title: "Arena Leaderboard | Sankalp26",
    description: "View participant standings in the Sankalp26 Arena.",
    index: true,
  },
};

function RouteMetadata() {
  const { pathname } = useLocation();
  const routePath = pathname.replace(/\/+$/, "") || "/";

  useEffect(() => {
    const metadata = ROUTE_METADATA[routePath] || {
      title: "Sankalp26",
      description: "Sankalp26 National Level Hackathon.",
      index: false,
    };
    const canonical = `${SITE_URL}${routePath === "/" ? "/" : routePath}`;
    document.title = metadata.title;

    const setMeta = (selector, attribute, value, content) => {
      let element = document.head.querySelector(selector);
      if (!element) {
        element = document.createElement("meta");
        element.setAttribute(attribute, value);
        document.head.appendChild(element);
      }
      element.setAttribute("content", content);
    };
    setMeta('meta[name="description"]', "name", "description", metadata.description);
    setMeta('meta[name="robots"]', "name", "robots", metadata.index ? "index, follow, max-image-preview:large" : "noindex, nofollow");
    setMeta('meta[property="og:title"]', "property", "og:title", metadata.title);
    setMeta('meta[property="og:description"]', "property", "og:description", metadata.description);
    setMeta('meta[property="og:url"]', "property", "og:url", canonical);
    setMeta('meta[name="twitter:title"]', "name", "twitter:title", metadata.title);
    setMeta('meta[name="twitter:description"]', "name", "twitter:description", metadata.description);

    let canonicalLink = document.head.querySelector('link[rel="canonical"]');
    if (!canonicalLink) {
      canonicalLink = document.createElement("link");
      canonicalLink.rel = "canonical";
      document.head.appendChild(canonicalLink);
    }
    canonicalLink.href = canonical;
  }, [routePath]);

  return null;
}

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
          <RouteMetadata />
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
