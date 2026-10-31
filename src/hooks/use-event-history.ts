"use client";

import { useCallback, useEffect, useState } from "react";

import type { StockEvent } from "@/lib/types";

const REFRESH_INTERVAL_MS = 15_000;

export function useEventHistory() {
  const [events, setEvents] = useState<StockEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/api/events", { cache: "no-store" });
      if (!response.ok) throw new Error(`Event history request failed with ${response.status}`);
      const payload = (await response.json()) as { events: StockEvent[] };
      setEvents(payload.events);
      setError(null);
    } catch {
      setError("Event history is temporarily unavailable. The last loaded events are still shown.");
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

  return { events, error, loading, refresh };
}
