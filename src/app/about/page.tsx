import type { Metadata } from "next";

export const metadata: Metadata = { title: "About" };

export default function AboutPage() {
  return (
    <main className="page-shell prose-page">
      <section className="page-heading"><div><p className="section-label">About the tracker</p><h1>Useful data, honest limits.</h1><p>This independent dashboard records publicly visible catalog availability.</p></div></section>
      <section className="prose-grid">
        <article><h2>What is tracked</h2><p>The monitor checks the public fragrance, discovery, and maison collections. It records confirmed restocks, sellouts, additions, removals, and price changes.</p></article>
        <article><h2>What quantity means</h2><p>Observed quantity is the most recent public quantity found on a product page. It can lag purchases and should not be treated as guaranteed inventory.</p></article>
        <article><h2>History begins at launch</h2><p>No historical events are invented or backfilled. Availability durations become more useful as the monitor collects real transitions.</p></article>
        <article><h2>Independent project</h2><p>Montagne Watch is unofficial and is not affiliated with, endorsed by, or operated by Montagne Parfums. Product images and names belong to their respective owner.</p></article>
      </section>
    </main>
  );
}
