"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowLeft, ArrowSquareOut, Clock, Package, TrendUp } from "@phosphor-icons/react";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EventFeed } from "@/components/event-feed";
import { StatusBadge } from "@/components/status-badge";
import { DashboardSkeleton, ErrorNotice } from "@/components/system-states";
import { formatDateTime, formatDuration, formatMoney, formatRelativeTime, productSourceUrl } from "@/lib/format";
import type { ProductPayload } from "@/lib/types";


export function ProductDashboard({ productId }: { productId: string }) {
  const [data, setData] = useState<ProductPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch(`/api/products/${encodeURIComponent(productId)}`, { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error(String(response.status));
        return (await response.json()) as ProductPayload;
      })
      .then((payload) => { if (active) setData(payload); })
      .catch(() => { if (active) setError("This product history could not be loaded."); });
    return () => { active = false; };
  }, [productId]);

  const completedPeriods = useMemo(
    () => data?.periods.filter((period) => period.duration_seconds !== null) ?? [],
    [data],
  );
  const chartData = useMemo(
    () => completedPeriods.slice(0, 12).reverse().map((period, index) => ({ period: index + 1, hours: Math.round(((period.duration_seconds ?? 0) / 3600) * 10) / 10 })),
    [completedPeriods],
  );

  if (error) return <main className="page-shell"><ErrorNotice message={error} /><Link className="back-link" href="/catalog"><ArrowLeft size={17} />Back to catalog</Link></main>;
  if (!data) return <DashboardSkeleton />;
  const { product, events } = data;

  return (
    <main className="page-shell">
      <Link className="back-link" href="/catalog"><ArrowLeft size={17} />Back to catalog</Link>
      <section className="product-detail-hero">
        <div className="detail-image-wrap"><Image src={product.image_url} alt="" fill sizes="(max-width: 760px) 100vw, 40vw" className="detail-image" priority /></div>
        <div className="detail-copy">
          <StatusBadge status={product.current_status} />
          <h1>{product.name}</h1>
          <div className="detail-price">{formatMoney(product.price_cents)}</div>
          <dl className="detail-facts">
            <div><dt>Observed quantity</dt><dd>{product.observed_quantity ?? "Audit pending"}</dd></div>
            <div><dt>Quantity checked</dt><dd>{formatRelativeTime(product.quantity_observed_at)}</dd></div>
            <div><dt>Category</dt><dd>{product.category}</dd></div>
            <div><dt>SKU</dt><dd>{product.sku ?? "Not recorded yet"}</dd></div>
          </dl>
          <a className="primary-button" href={productSourceUrl(product.url_path)} target="_blank" rel="noreferrer">View at Montagne <ArrowSquareOut size={17} /></a>
        </div>
      </section>

      <section className="stats-grid detail-stats">
        <DetailStat icon={<TrendUp size={20} />} label="Recorded restocks" value={product.restock_count} />
        <DetailStat icon={<Clock size={20} />} label="Average availability" value={formatDuration(product.average_in_stock_duration_seconds)} />
        <DetailStat icon={<Package size={20} />} label="Last status change" value={formatDateTime(product.last_changed_at)} compact />
      </section>

      <section className="dashboard-grid product-history-grid">
        <div className="panel chart-panel"><div className="panel-heading"><div><h2>Availability windows</h2><p>Latest 12 completed in-stock periods. Statistics above use the full history.</p></div></div>{chartData.length ? <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData}><CartesianGrid stroke="var(--line)" vertical={false} /><XAxis dataKey="period" tickLine={false} axisLine={false} /><YAxis tickLine={false} axisLine={false} unit="h" /><Tooltip contentStyle={{ background: "var(--surface-raised)", border: "1px solid var(--line)", borderRadius: 12 }} /><Bar dataKey="hours" fill="#38d996" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div> : <div className="empty-chart">A completed restock window is needed before this chart can be calculated.</div>}</div>
        <div className="panel"><div className="panel-heading"><div><h2>Product timeline</h2><p>Confirmed changes for this product.</p></div></div><EventFeed events={events} /></div>
      </section>
    </main>
  );
}

function DetailStat({ icon, label, value, compact = false }: { icon: React.ReactNode; label: string; value: React.ReactNode; compact?: boolean }) {
  return <article className="stat-card"><div className="stat-card-label">{icon}<span>{label}</span></div><strong className={compact ? "stat-value small" : "stat-value"}>{value}</strong></article>;
}
