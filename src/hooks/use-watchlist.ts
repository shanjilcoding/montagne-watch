"use client";

import { useEffect, useState } from "react";


const STORAGE_KEY = "montagne-watchlist";

export function useWatchlist() {
  const [watched, setWatched] = useState<Set<string>>(new Set());

  useEffect(() => {
    const timer = window.setTimeout(() => {
      try {
        const stored = JSON.parse(window.localStorage.getItem(STORAGE_KEY) ?? "[]") as string[];
        setWatched(new Set(stored));
      } catch {
        setWatched(new Set());
      }
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  function toggle(productId: string) {
    setWatched((current) => {
      const next = new Set(current);
      if (next.has(productId)) next.delete(productId);
      else next.add(productId);
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify([...next]));
      return next;
    });
  }

  return { watched, toggle };
}
