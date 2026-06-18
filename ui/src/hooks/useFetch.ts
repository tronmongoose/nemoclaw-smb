/** Generic fetch hook. Returns null data on failure — no crash, no infinite spinner. */

import { useState, useEffect, useCallback, useRef } from "react";
import { apiFetch } from "../lib/api";

interface FetchState<T> {
  data: T | null;
  loading: boolean;
  refetch: () => void;
}

export function useFetch<T>(path: string): FetchState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const mountedRef = useRef(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    const result = await apiFetch<T>(path);
    if (mountedRef.current) {
      setData(result);
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    mountedRef.current = true;
    void fetchData();
    return () => {
      mountedRef.current = false;
    };
  }, [fetchData]);

  return { data, loading, refetch: fetchData };
}
