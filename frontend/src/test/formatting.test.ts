import { describe, it, expect } from "vitest";
import { formatDuration, formatPercent, formatDistance, formatAge } from "@/utils/formatting";

describe("formatting utilities", () => {
  it("formatDuration returns em-dash for null", () => {
    expect(formatDuration(null)).toBe("—");
  });

  it("formatDuration formats seconds only", () => {
    expect(formatDuration(45)).toBe("45s");
  });

  it("formatDuration formats minutes and seconds", () => {
    expect(formatDuration(270)).toBe("4m 30s");
  });

  it("formatDuration formats whole minutes", () => {
    expect(formatDuration(120)).toBe("2m");
  });

  it("formatPercent returns em-dash for null", () => {
    expect(formatPercent(null)).toBe("—");
  });

  it("formatPercent formats 0.75 as 75%", () => {
    expect(formatPercent(0.75)).toBe("75%");
  });

  it("formatDistance returns em-dash for null", () => {
    expect(formatDistance(null)).toBe("—");
  });

  it("formatDistance formats metres under 1000", () => {
    expect(formatDistance(500)).toBe("500 m");
  });

  it("formatDistance formats kilometres for >= 1000", () => {
    expect(formatDistance(2500)).toBe("2.5 km");
  });
});
