import { useEffect, useRef } from "react";

interface UseAutoRefreshOptions {
  enabled: boolean;
  intervalMs: number;
  onRefresh: () => void | Promise<void>;
}

export function useAutoRefresh({
  enabled,
  intervalMs,
  onRefresh,
}: UseAutoRefreshOptions) {
  const refreshRef = useRef(onRefresh);

  useEffect(() => {
    refreshRef.current = onRefresh;
  }, [onRefresh]);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const tick = () => {
      if (document.visibilityState !== "visible") {
        return;
      }

      void refreshRef.current();
    };

    const intervalId = window.setInterval(tick, intervalMs);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [enabled, intervalMs]);
}
