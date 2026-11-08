import type { GetTeacherCourseResponse } from "@api";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react-native";
import type { ReactNode } from "react";

import { api } from "../api";
import { keys, useUpdateSettings } from "../queries";

jest.mock("../api", () => ({ api: { updateSettings: jest.fn(), teacherCourse: jest.fn() } }));

const updateSettings = jest.mocked(api.updateSettings);

const settings = {
  hintsOnly: false,
  useSolutionKeys: true,
  citeMaterials: true,
  deadlineReminders: false,
};
const course = { settings, materials: [] } as unknown as GetTeacherCourseResponse;

async function setup() {
  // gcTime: Infinity keeps React Query from leaving cleanup timers that stop Jest from exiting.
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: Infinity, gcTime: Infinity },
      mutations: { gcTime: Infinity },
    },
  });
  client.setQueryData(keys.teacherCourse("c1"), course);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  const { result } = await renderHook(() => useUpdateSettings("c1"), { wrapper });
  const cached = () => client.getQueryData<GetTeacherCourseResponse>(keys.teacherCourse("c1"));
  return { result, cached };
}

describe("useUpdateSettings", () => {
  beforeEach(() => jest.clearAllMocks());

  it("shows the change right away, before the server answers", async () => {
    let finish!: () => void;
    updateSettings.mockReturnValue(new Promise((resolve) => (finish = () => resolve({} as never))));
    const { result, cached } = await setup();

    await act(() => result.current.mutate({ hintsOnly: true }));
    await waitFor(() => expect(cached()?.settings).toEqual({ ...settings, hintsOnly: true }));
    expect(updateSettings).toHaveBeenCalledWith("c1", { hintsOnly: true });

    await act(async () => finish());
  });

  it("rolls back when the server refuses", async () => {
    updateSettings.mockRejectedValue(new Error("nope"));
    const { result, cached } = await setup();

    await act(() => result.current.mutate({ hintsOnly: true }));
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(cached()?.settings).toEqual(settings);
  });
});
