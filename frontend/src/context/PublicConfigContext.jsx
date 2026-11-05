import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { toast } from "sonner";
import { api, formatErr } from "@/lib/api";

const PublicConfig = createContext({ topics: [], timeline: {}, portals: {} });

export function PublicConfigProvider({ children }) {
  const [config, setConfig] = useState({ topics: [], timeline: {}, portals: {} });
  const refresh = useCallback(() => api.get("/public/meta")
    .then(({ data }) => {
      setConfig(data);
      toast.dismiss("public-meta-error");
    })
    .catch((error) => toast.error(formatErr(error), { id: "public-meta-error" })), []);
  useEffect(() => {
    refresh();
    window.addEventListener("focus", refresh);
    return () => window.removeEventListener("focus", refresh);
  }, [refresh]);
  return <PublicConfig.Provider value={{ ...config, refresh }}>{children}</PublicConfig.Provider>;
}

export const usePublicConfig = () => useContext(PublicConfig);