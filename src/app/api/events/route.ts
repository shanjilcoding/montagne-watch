import { NextResponse } from "next/server";

import { fetchBackend } from "@/lib/backend";


export async function GET() {
  try {
    const response = await fetchBackend("/api/events");
    const body = await response.text();
    return new NextResponse(body, {
      status: response.status,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "public, s-maxage=10, stale-while-revalidate=30",
      },
    });
  } catch {
    return NextResponse.json({ error: "events_unavailable" }, { status: 503 });
  }
}
