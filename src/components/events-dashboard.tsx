"use client";

import { useMemo, useState } from "react";

import { EventFeed } from "@/components/event-feed";
import { DashboardSkeleton, ErrorNotice } from "@/components/system-states";
import { useEventHistory } from "@/hooks/use-event-history";
import type { EventType } from "@/lib/types";


type EventFilter = "all" | EventType;

export function EventsDashboard() {
  const { events, error, loading, refresh } = useEventHistory();
  const [filter, setFilter] = useState<EventFilter>("all");
  const visible = useMemo(
    () => events?.filter((event) => filter === "all" || event.event_type === filter) ?? [],
    [events, filter],
  );

  if (loading && !events) return <DashboardSkeleton />;
  if (!events) return <main className="page-shell"><ErrorNotice message={error ?? "No event data loaded."} onRetry={refresh} /></main>;

  return (
    <main className="page-shell">
      <section className="page-heading">
        <div><p className="section-label">Availability history</p><h1>Restocks and catalog events.</h1><p>Every confirmed state change recorded from the moment tracking started.</p></div>
        <div className="result-count"><strong>{visible.length}</strong><span>recorded events</span></div>
      </section>
      {error ? <ErrorNotice message={error} onRetry={refresh} /> : null}
      <div className="event-filter" role="group" aria-label="Filter events">
        {(["all", "restock", "sold_out", "new_product", "price_change", "removed"] as EventFilter[]).map((option) => (
          <button key={option} className={filter === option ? "active" : ""} onClick={() => setFilter(option)}>
            {option === "all" ? "All" : option.replaceAll("_", " ")}
          </button>
        ))}
      </div>
      <section className="panel events-page-panel"><EventFeed events={visible} /></section>
    </main>
  );
}
