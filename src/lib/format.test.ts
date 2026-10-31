import { describe, expect, it } from "vitest";

import { eventLabel, formatDuration, formatMoney, formatRelativeTime } from "./format";


describe("format helpers", () => {
  it("formats money from integer cents", () => {
    expect(formatMoney(4500)).toBe("$45.00");
    expect(formatMoney(null)).toBe("Price unavailable");
  });

  it("formats durations into shopper-readable values", () => {
    expect(formatDuration(45)).toBe("45 seconds");
    expect(formatDuration(600)).toBe("10 minutes");
    expect(formatDuration(9000)).toBe("2 hours 30 minutes");
  });

  it("uses clear event labels", () => {
    expect(eventLabel("restock")).toBe("Restocked");
    expect(eventLabel("sold_out")).toBe("Sold out");
    expect(eventLabel("new_product")).toBe("New product");
  });

  it("formats relative time against an explicit clock", () => {
    expect(
      formatRelativeTime("2026-10-29T22:55:00Z", new Date("2026-10-29T23:00:00Z")),
    ).toBe("5 minutes ago");
  });
});
