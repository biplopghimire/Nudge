import { act, renderHook } from "@testing-library/react-native";

import { usePullToRefresh } from "../pull-to-refresh";

function deferred() {
  let resolve!: () => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<void>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("usePullToRefresh", () => {
  it("is not refreshing until the user pulls", async () => {
    const { result } = await renderHook(() => usePullToRefresh(jest.fn()));
    expect(result.current.refreshing).toBe(false);
  });

  it("shows the spinner only while the pulled refetch runs", async () => {
    const pending = deferred();
    const refetch = jest.fn(() => pending.promise);
    const { result } = await renderHook(() => usePullToRefresh(refetch));

    let done!: Promise<void>;
    await act(async () => {
      done = result.current.onRefresh();
    });
    expect(refetch).toHaveBeenCalledTimes(1);
    expect(result.current.refreshing).toBe(true);

    await act(async () => {
      pending.resolve();
      await done;
    });
    expect(result.current.refreshing).toBe(false);
  });

  it("hides the spinner even when the refetch fails", async () => {
    const pending = deferred();
    const { result } = await renderHook(() => usePullToRefresh(() => pending.promise));

    let done!: Promise<void>;
    await act(async () => {
      done = result.current.onRefresh();
    });
    await act(async () => {
      pending.reject(new Error("offline"));
      await done.catch(() => {});
    });
    expect(result.current.refreshing).toBe(false);
  });
});
