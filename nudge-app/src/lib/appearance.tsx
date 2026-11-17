import * as SecureStore from "expo-secure-store";
import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Uniwind } from "uniwind";

export type AppearanceChoice = "system" | "light" | "dark";

const KEY = "nudge.appearance";

type AppearanceContextValue = {
  appearance: AppearanceChoice;
  setAppearance: (appearance: AppearanceChoice) => Promise<void>;
};

const AppearanceContext = createContext<AppearanceContextValue | null>(null);

export function AppearanceProvider({ children }: { children: ReactNode }) {
  const [appearance, setAppearanceState] = useState<AppearanceChoice>("system");

  useEffect(() => {
    SecureStore.getItemAsync(KEY)
      .then((saved) => {
        const choice: AppearanceChoice =
          saved === "light" || saved === "dark" || saved === "system" ? saved : "system";
        setAppearanceState(choice);
        Uniwind.setTheme(choice);
      })
      .catch(() => Uniwind.setTheme("system"));
  }, []);

  const setAppearance = useCallback(async (choice: AppearanceChoice) => {
    setAppearanceState(choice);
    Uniwind.setTheme(choice);
    await SecureStore.setItemAsync(KEY, choice).catch(() => {});
  }, []);

  const value = useMemo(
    () => ({ appearance, setAppearance }),
    [appearance, setAppearance],
  );

  return <AppearanceContext.Provider value={value}>{children}</AppearanceContext.Provider>;
}

export function useAppearance() {
  const value = useContext(AppearanceContext);
  if (!value) throw new Error("useAppearance must be used inside AppearanceProvider");
  return value;
}
