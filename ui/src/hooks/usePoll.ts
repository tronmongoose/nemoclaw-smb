/** Polling fetch hook — refreshes at a fixed interval while mounted. */

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "../lib/api";

interface PollState<T> {
  data: T | null;
  loading: boolean;
  refetch: () => void;
}

export function usePoll<T>(path: string, intervalMs: number): PollState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const mountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    const result = await apiFetch<T>(path);
    if (mountedRef.current) {
      setData(result);
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    mountedRef.current = true;
    void fetchData();
    const id = setInterval(() => void fetchData(), intervalMs);
    return () => {
      mountedRef.current = false;
      clearInterval(id);
    };
  }, [fetchData, intervalMs]);

  return { data, loading, refetch: fetchData };
}
