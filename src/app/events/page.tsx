import type { Metadata } from "next";

import { EventsDashboard } from "@/components/events-dashboard";

export const metadata: Metadata = { title: "Events" };

export default function EventsPage() {
  return <EventsDashboard />;
}
