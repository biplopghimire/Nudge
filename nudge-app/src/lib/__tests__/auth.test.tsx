import type { User } from "@api";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react-native";
import * as SecureStore from "expo-secure-store";
import type { ReactNode } from "react";

import { api, setSession } from "../api";
import { AuthProvider, useAuth } from "../auth";

jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));
jest.mock("../api", () => ({
  api: { login: jest.fn(), signup: jest.fn() },
  setSession: jest.fn(),
}));

const store = jest.mocked(SecureStore);
const login = jest.mocked(api.login);
const signup = jest.mocked(api.signup);

const ada: User = { id: "u1", name: "Ada", email: "ada@cmu.edu", role: "student" };

async function setup(saved: string | null = null) {
  store.getItemAsync.mockResolvedValue(saved);
  // gcTime: Infinity keeps React Query from leaving cleanup timers that stop Jest from exiting.
  const client = new QueryClient({ defaultOptions: { queries: { gcTime: Infinity } } });
  client.setQueryData(["student", "me"], { cached: true });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
  const { result } = await renderHook(() => useAuth(), { wrapper });
  return { result, client };
}

describe("AuthProvider", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    store.setItemAsync.mockResolvedValue();
    store.deleteItemAsync.mockResolvedValue();
  });

  it("is signed out when nothing is saved", async () => {
    const { result } = await setup();
    await waitFor(() => expect(result.current.status).toBe("signedOut"));
    expect(result.current.user).toBeNull();
  });

  it("restores a saved session", async () => {
    const { result } = await setup(JSON.stringify({ token: "saved", user: ada }));
    await waitFor(() => expect(result.current.status).toBe("signedIn"));
    expect(result.current.user).toEqual(ada);
    expect(setSession).toHaveBeenCalledWith("saved", expect.any(Function));
  });

  it("is signed out when the saved session can't be read", async () => {
    const { result } = await setup("not json");
    await waitFor(() => expect(result.current.status).toBe("signedOut"));
  });

  it("signs in with a trimmed email and saves the session", async () => {
    login.mockResolvedValue({ token: "new", user: ada });
    const { result } = await setup();
    await waitFor(() => expect(result.current.status).toBe("signedOut"));

    await act(async () => {
      await expect(result.current.signIn("  ada@cmu.edu ", "pw")).resolves.toEqual(ada);
    });
    expect(login).toHaveBeenCalledWith("ada@cmu.edu", "pw");
    expect(result.current.status).toBe("signedIn");
    expect(store.setItemAsync).toHaveBeenCalledWith(
      "nudge.session",
      JSON.stringify({ token: "new", user: ada })
    );
  });

  it("signs up with a trimmed name and email", async () => {
    signup.mockResolvedValue({ token: "new", user: ada });
    const { result } = await setup();
    await waitFor(() => expect(result.current.status).toBe("signedOut"));

    await act(() => result.current.signUp(" Ada ", " ada@cmu.edu", "pw", "student"));
    expect(signup).toHaveBeenCalledWith("Ada", "ada@cmu.edu", "pw", "student");
    expect(result.current.user).toEqual(ada);
  });

  it("signing out forgets the session and the cached data", async () => {
    const { result, client } = await setup(JSON.stringify({ token: "saved", user: ada }));
    await waitFor(() => expect(result.current.status).toBe("signedIn"));

    await act(() => result.current.signOut());
    expect(result.current.status).toBe("signedOut");
    expect(result.current.user).toBeNull();
    expect(setSession).toHaveBeenLastCalledWith(null);
    expect(store.deleteItemAsync).toHaveBeenCalledWith("nudge.session");
    expect(client.getQueryData(["student", "me"])).toBeUndefined();
  });

  it("signs out when the API reports the token expired", async () => {
    const { result } = await setup(JSON.stringify({ token: "saved", user: ada }));
    await waitFor(() => expect(result.current.status).toBe("signedIn"));

    const onUnauthorized = jest.mocked(setSession).mock.calls.at(-1)?.[1];
    await act(() => onUnauthorized?.());
    await waitFor(() => expect(result.current.status).toBe("signedOut"));
  });
});
