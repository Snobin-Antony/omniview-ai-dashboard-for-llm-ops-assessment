import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { SEED_USERS } from "../types";

interface AppState {
  userId: string;
  setUserId: (id: string) => void;
  workspaceId: string | null;
  setWorkspaceId: (id: string | null) => void;
  users: typeof SEED_USERS;
}

const Ctx = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [userId, setUserId] = useState<string>(
    () => localStorage.getItem("omniview_user") || SEED_USERS[0].id
  );
  const [workspaceId, setWorkspaceId] = useState<string | null>(
    () => localStorage.getItem("omniview_workspace")
  );

  useEffect(() => {
    localStorage.setItem("omniview_user", userId);
  }, [userId]);

  useEffect(() => {
    if (workspaceId) localStorage.setItem("omniview_workspace", workspaceId);
  }, [workspaceId]);

  const value = useMemo(
    () => ({
      userId,
      setUserId,
      workspaceId,
      setWorkspaceId,
      users: SEED_USERS,
    }),
    [userId, workspaceId]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp outside provider");
  return ctx;
}
