import { createContext, useContext, useEffect, useState } from "react";
import { api, clearAccessToken } from "@/lib/api";

const AuthCtx = createContext(null);

export const homeFor = (role) => ({ admin: "/admin", judge: "/judge", member: "/dashboard" }[role] || "/dashboard");

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    localStorage.removeItem("sk_token");
    api.get("/auth/me").then((r) => setUser(r.data)).catch(() => setUser(false));
  }, []);

  const accept = (data) => {
    setUser(data.user);
    return data.user;
  };

  const login = async (email, password) => accept((await api.post("/auth/login", { email, password })).data);
  // register now auto-logs in — returns { user, token, team_id }
  const register = async (payload) => accept((await api.post("/auth/register", payload)).data);
  const activate = async (payload) => accept((await api.post("/auth/activate", payload)).data);
  const changePassword = async (payload) => accept((await api.post("/auth/change-password", payload)).data);
  const logout = async () => {
    await api.post("/auth/logout");
    clearAccessToken();
    setUser(false);
  };

  return <AuthCtx.Provider value={{ user, login, register, activate, changePassword, logout }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
