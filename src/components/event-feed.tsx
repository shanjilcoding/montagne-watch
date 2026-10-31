import Link from "next/link";
import { ArrowDown, ArrowUp, Package, Tag } from "@phosphor-icons/react";

import { eventLabel, formatDuration, formatMoney, formatRelativeTime } from "@/lib/format";
import type { StockEvent } from "@/lib/types";


function EventIcon({ type }: { type: StockEvent["event_type"] }) {
  if (type === "restock") return <ArrowUp size={19} weight="bold" />;
  if (type === "sold_out") return <ArrowDown size={19} weight="bold" />;
  if (type === "price_change") return <Tag size={19} weight="bold" />;
  return <Package size={19} weight="bold" />;
}

export function EventFeed({ events, limit }: { events: StockEvent[]; limit?: number }) {
  const visible = typeof limit === "number" ? events.slice(0, limit) : events;
  if (!visible.length) {
    return (
      <div className="empty-state">
        <ClockPlaceholder />
        <h3>History starts here</h3>
        <p>Restocks, sellouts, new products, and price changes will appear after tracking begins.</p>
      </div>
    );
  }

  return (
    <div className="event-list">
      {visible.map((event) => (
        <article className={`event-row event-${event.event_type}`} key={event.event_id}>
          <div className="event-icon" aria-hidden="true"><EventIcon type={event.event_type} /></div>
          <div className="event-copy">
            <div className="event-heading">
              <span className="event-type">{eventLabel(event.event_type)}</span>
              <span className="event-time" title={new Date(event.observed_at).toLocaleString()}>
                {formatRelativeTime(event.observed_at)}
              </span>
            </div>
            <Link href={`/products/${encodeURIComponent(event.product_id)}`} className="event-product">
              {event.name}
            </Link>
            <p className="event-detail">
              {event.event_type === "sold_out" && event.duration_seconds !== null
                ? `Available for ${formatDuration(event.duration_seconds)}`
                : event.event_type === "price_change"
                  ? `${formatMoney(event.previous_price_cents)} to ${formatMoney(event.new_price_cents)}`
                  : event.new_quantity !== null
                    ? `${event.new_quantity} units observed`
                    : formatMoney(event.price_cents)}
            </p>
          </div>
        </article>
      ))}
    </div>
  );
}

function ClockPlaceholder() {
  return <div className="empty-symbol" aria-hidden="true"><Package size={28} /></div>;
}
