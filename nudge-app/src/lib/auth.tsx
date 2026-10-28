/**
 * Who is signed in. The login token lives in the iPhone's secure storage
 * (expo-secure-store), so it survives restarts and never sits in plain files.
 */
import type { Role, User } from "@api";
import { useQueryClient } from "@tanstack/react-query";
import * as SecureStore from "expo-secure-store";
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { api, setSession } from "./api";

const KEY = "nudge.session";

type Session = { token: string; user: User };
type Status = "loading" | "signedOut" | "signedIn";

type AuthContextValue = {
  status: Status;
  user: User | null;
  signIn: (email: string, password: string) => Promise<User>;
  signUp: (name: string, email: string, password: string, role: Role) => Promise<User>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [session, setSessionState] = useState<Session | null>(null);
  const [status, setStatus] = useState<Status>("loading");

  const signOut = useCallback(async () => {
    setSession(null);
    setSessionState(null);
    setStatus("signedOut");
    queryClient.clear();
    await SecureStore.deleteItemAsync(KEY).catch(() => {});
  }, [queryClient]);

  const start = useCallback(
    async (next: Session) => {
      setSession(next.token, () => void signOut());
      setSessionState(next);
      setStatus("signedIn");
      await SecureStore.setItemAsync(KEY, JSON.stringify(next));
      return next.user;
    },
    [signOut],
  );

  useEffect(() => {
    SecureStore.getItemAsync(KEY)
      .then((saved) => {
        if (!saved) return setStatus("signedOut");
        const restored = JSON.parse(saved) as Session;
        setSession(restored.token, () => void signOut());
        setSessionState(restored);
        setStatus("signedIn");
      })
      .catch(() => setStatus("signedOut"));
  }, [signOut]);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user: session?.user ?? null,
      signIn: async (email, password) => start(await api.login(email.trim(), password)),
      signUp: async (name, email, password, role) =>
        start(await api.signup(name.trim(), email.trim(), password, role)),
      signOut,
    }),
    [status, session, start, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}
