"use client";

import { useCallback, useEffect, useState } from "react";

import type { DashboardState } from "@/lib/types";


const REFRESH_INTERVAL_MS = 15_000;

export function useDashboardState() {
  const [data, setData] = useState<DashboardState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/state", { cache: "no-store" });
      if (!response.ok) throw new Error(`Dashboard request failed with ${response.status}`);
      const payload = (await response.json()) as DashboardState;
      setData((current) => (current?.revision === payload.revision ? current : payload));
      setError(null);
    } catch {
      setError("Live inventory is temporarily unavailable. The last loaded data is still shown.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initial = window.setTimeout(() => void refresh(), 0);
    const timer = window.setInterval(() => void refresh(), REFRESH_INTERVAL_MS);
    return () => {
      window.clearTimeout(initial);
      window.clearInterval(timer);
    };
  }, [refresh]);

  return { data, error, loading, refresh };
}
