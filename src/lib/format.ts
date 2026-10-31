import type { EventType } from "./types";


export function formatMoney(cents: number | null): string {
  if (cents === null) return "Price unavailable";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  }).format(cents / 100);
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds < 0) return "Not enough data";
  if (seconds < 60) return `${Math.round(seconds)} ${Math.round(seconds) === 1 ? "second" : "seconds"}`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} ${minutes === 1 ? "minute" : "minutes"}`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (hours < 24) {
    return remainingMinutes
      ? `${hours} ${hours === 1 ? "hour" : "hours"} ${remainingMinutes} minutes`
      : `${hours} ${hours === 1 ? "hour" : "hours"}`;
  }
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;
  return remainingHours
    ? `${days} ${days === 1 ? "day" : "days"} ${remainingHours} hours`
    : `${days} ${days === 1 ? "day" : "days"}`;
}

export function formatDateTime(value: string | null): string {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatRelativeTime(value: string | null, now = new Date()): string {
  if (!value) return "Not checked yet";
  const differenceSeconds = Math.round((new Date(value).getTime() - now.getTime()) / 1000);
  const absolute = Math.abs(differenceSeconds);
  const formatter = new Intl.RelativeTimeFormat("en-US", { numeric: "always" });
  if (absolute < 60) return formatter.format(differenceSeconds, "second");
  if (absolute < 3600) return formatter.format(Math.round(differenceSeconds / 60), "minute");
  if (absolute < 86400) return formatter.format(Math.round(differenceSeconds / 3600), "hour");
  return formatter.format(Math.round(differenceSeconds / 86400), "day");
}

export function eventLabel(eventType: EventType): string {
  const labels: Record<EventType, string> = {
    restock: "Restocked",
    sold_out: "Sold out",
    new_product: "New product",
    removed: "Removed",
    price_change: "Price changed",
  };
  return labels[eventType];
}

export function productSourceUrl(path: string): string {
  return `https://www.montagneparfums.com${path}`;
}
