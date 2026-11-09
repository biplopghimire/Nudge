import { useCallback, useState } from "react";

/**
 * Props for a `RefreshControl`. The spinner shows only while a refresh the user
 * pulled for is running. Background refetches (polling while uploads process,
 * invalidations after a change) stay silent; showing the spinner for those made
 * the screen jump down and back every couple of seconds (issue #22).
 */
export function usePullToRefresh(refetch: () => Promise<unknown>) {
  const [refreshing, setRefreshing] = useState(false);
  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await refetch();
    } finally {
      setRefreshing(false);
    }
  }, [refetch]);
  return { refreshing, onRefresh };
}
