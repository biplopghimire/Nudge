import { act, renderHook, waitFor } from "@testing-library/react-native";
import * as SecureStore from "expo-secure-store";
import type { ReactNode } from "react";
import { Uniwind } from "uniwind";

import { AppearanceProvider, useAppearance } from "../appearance";

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
}));
jest.mock("uniwind", () => ({
  Uniwind: { setTheme: jest.fn() },
}));

const store = jest.mocked(SecureStore);
const setTheme = jest.mocked(Uniwind.setTheme);

function wrapper({ children }: { children: ReactNode }) {
  return <AppearanceProvider>{children}</AppearanceProvider>;
}

describe("AppearanceProvider", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    store.setItemAsync.mockResolvedValue();
  });

  it("defaults to system", async () => {
    store.getItemAsync.mockResolvedValue(null);
    const { result } = await renderHook(() => useAppearance(), { wrapper });

    await waitFor(() => expect(result.current.appearance).toBe("system"));
    expect(setTheme).toHaveBeenCalledWith("system");
  });

  it("restores a saved light choice", async () => {
    store.getItemAsync.mockResolvedValue("light");
    const { result } = await renderHook(() => useAppearance(), { wrapper });

    await waitFor(() => expect(result.current.appearance).toBe("light"));
    expect(setTheme).toHaveBeenCalledWith("light");
  });

  it("changes immediately and persists the choice", async () => {
    store.getItemAsync.mockResolvedValue("system");
    const { result } = await renderHook(() => useAppearance(), { wrapper });

    await act(() => result.current.setAppearance("dark"));

    expect(result.current.appearance).toBe("dark");
    expect(setTheme).toHaveBeenCalledWith("dark");
    expect(store.setItemAsync).toHaveBeenCalledWith("nudge.appearance", "dark");
  });
});
