import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage, isCancel, withSignal } from "../services/api";

/**
 * Data-fetching hook with loading / error / reload semantics.
 *
 * - Every request gets an AbortSignal; a request is cancelled when the page
 *   unmounts or its inputs change, so stale requests never pile up.
 * - A hard timeout turns a stalled request into a visible error with a Retry
 *   button instead of an endless "Loading…".
 */
const TIMEOUT_MS = 20_000;

export function useApi<T>(fn: (signal: AbortSignal) => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const ctrl = useRef<AbortController | null>(null);

  const load = useCallback(async () => {
    ctrl.current?.abort();
    const c = new AbortController();
    ctrl.current = c;
    const timer = window.setTimeout(() => c.abort("timeout"), TIMEOUT_MS);
    setLoading(true);
    setError(null);
    try {
      const d = await withSignal(c.signal, () => fn(c.signal));
      if (ctrl.current === c) setData(d);
    } catch (e) {
      if (ctrl.current !== c) return;            // superseded by a newer request
      if (c.signal.reason === "timeout") {
        setError("The server is taking too long to respond. Check that the backend is running, then retry.");
      } else if (!isCancel(e)) {
        setError(errorMessage(e));
      }
    } finally {
      window.clearTimeout(timer);
      if (ctrl.current === c) setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    void load();
    return () => ctrl.current?.abort();
  }, [load]);

  return { data, error, loading, reload: load, setData };
}
