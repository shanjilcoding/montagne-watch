"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight, CheckCircle, Clock, Package, Pulse, Warning } from "@phosphor-icons/react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EventFeed } from "@/components/event-feed";
import { ErrorNotice, DashboardSkeleton } from "@/components/system-states";
import { formatDuration, formatRelativeTime } from "@/lib/format";
import type { StockEvent } from "@/lib/types";
import { useDashboardState } from "@/hooks/use-dashboard-state";


function eventSeries(events: StockEvent[]) {
  const days = new Map<string, { date: string; restocks: number; sellouts: number }>();
  for (let offset = 6; offset >= 0; offset -= 1) {
    const day = new Date();
    day.setDate(day.getDate() - offset);
    const key = day.toISOString().slice(0, 10);
    days.set(key, { date: day.toLocaleDateString("en-US", { weekday: "short" }), restocks: 0, sellouts: 0 });
  }
  for (const event of events) {
    const key = event.observed_at.slice(0, 10);
    const bucket = days.get(key);
    if (!bucket) continue;
    if (event.event_type === "restock") bucket.restocks += 1;
    if (event.event_type === "sold_out") bucket.sellouts += 1;
  }
  return [...days.values()];
}

export function OverviewDashboard() {
  const { data, error, loading, refresh } = useDashboardState();
  if (loading && !data) return <DashboardSkeleton />;
  if (!data) return <main className="page-shell"><ErrorNotice message={error ?? "No data loaded."} onRetry={refresh} /></main>;

  const { summary, products, events, activity_events } = data;
  const availability = summary.total_products
    ? Math.round((summary.in_stock / summary.total_products) * 100)
    : 0;
  const recentlyChanged = [...products]
    .sort((a, b) => new Date(b.last_changed_at).getTime() - new Date(a.last_changed_at).getTime())
    .slice(0, 4);

  return (
    <main className="page-shell">
      <section className="overview-hero">
        <div>
          <p className="section-label">Unofficial inventory tracker</p>
          <h1>Know what is available before it disappears.</h1>
          <p className="hero-copy">Live availability, restock history, and sellout timing across the complete Montagne catalog.</p>
        </div>
        <div className="monitor-card">
          <div className="monitor-status"><Pulse size={20} weight="fill" /><span>Monitor healthy</span></div>
          <strong>{formatRelativeTime(summary.last_successful_check)}</strong>
          <span>Last complete catalog check</span>
        </div>
      </section>

      {error ? <ErrorNotice message={error} onRetry={refresh} /> : null}

      <section className="stats-grid" aria-label="Catalog statistics">
        <StatCard icon={<Package size={21} />} label="Catalog" value={summary.total_products} detail="tracked products" />
        <StatCard icon={<CheckCircle size={21} />} label="Available" value={summary.in_stock} detail={`${availability}% of catalog`} accent />
        <StatCard icon={<Warning size={21} />} label="Sold out" value={summary.sold_out} detail="currently unavailable" />
        <StatCard icon={<Clock size={21} />} label="Average window" value={formatDuration(summary.average_in_stock_seconds)} detail="completed in-stock periods" compact />
      </section>

      <section className="dashboard-grid">
        <div className="panel chart-panel">
          <div className="panel-heading">
            <div><h2>Availability activity</h2><p>Restocks and sellouts recorded over the last seven days.</p></div>
          </div>
          <div className="chart-wrap" role="img" aria-label="Seven day restock and sellout chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={eventSeries(activity_events)} margin={{ top: 10, right: 4, left: -28, bottom: 0 }}>
                <defs>
                  <linearGradient id="restockFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#38d996" stopOpacity={0.35} /><stop offset="100%" stopColor="#38d996" stopOpacity={0} /></linearGradient>
                </defs>
                <CartesianGrid stroke="var(--line)" vertical={false} />
                <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fill: "var(--muted)", fontSize: 12 }} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: "var(--muted)", fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--line)", borderRadius: 12 }} />
                <Area type="monotone" dataKey="restocks" stroke="#38d996" fill="url(#restockFill)" strokeWidth={2} />
                <Area type="monotone" dataKey="sellouts" stroke="#9ca3af" fill="transparent" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="panel recent-panel">
          <div className="panel-heading inline"><div><h2>Recent changes</h2><p>Latest catalog state changes.</p></div><Link href="/events">All events <ArrowRight size={16} /></Link></div>
          <EventFeed events={events} limit={5} />
        </div>
      </section>

      <section className="panel tracked-panel">
        <div className="panel-heading inline"><div><h2>Recently updated</h2><p>Products with the newest availability changes.</p></div><Link href="/catalog">Browse catalog <ArrowRight size={16} /></Link></div>
        <div className="compact-product-grid">
          {recentlyChanged.map((product) => (
            <Link className="compact-product" href={`/products/${encodeURIComponent(product.product_id)}`} key={product.product_id}>
              <Image src={product.image_url} alt="" width={58} height={58} />
              <div><strong>{product.name}</strong><span>{product.current_status === "in_stock" ? "In stock" : "Sold out"}</span></div>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}

function StatCard({ icon, label, value, detail, accent = false, compact = false }: { icon: React.ReactNode; label: string; value: React.ReactNode; detail: string; accent?: boolean; compact?: boolean }) {
  return <article className={accent ? "stat-card accent" : "stat-card"}><div className="stat-card-label">{icon}<span>{label}</span></div><strong className={compact ? "stat-value compact" : "stat-value"}>{value}</strong><span className="stat-detail">{detail}</span></article>;
}
