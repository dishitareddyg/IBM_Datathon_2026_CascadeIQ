import { describe, it, expect } from "vitest";
import { bboxToLeafletBounds, bboxCentre, haversineMetres } from "@/utils/geo";
import type { BoundingBox } from "@/types/api";

const BLR: BoundingBox = { min_lat: 12.75, min_lon: 77.35, max_lat: 13.18, max_lon: 77.85 };

describe("geo utilities", () => {
  it("bboxToLeafletBounds produces correct SW/NE corners", () => {
    const bounds = bboxToLeafletBounds(BLR);
    expect(bounds[0]).toEqual([12.75, 77.35]);
    expect(bounds[1]).toEqual([13.18, 77.85]);
  });

  it("bboxCentre computes midpoint", () => {
    const [lat, lon] = bboxCentre(BLR);
    expect(lat).toBeCloseTo(12.965, 2);
    expect(lon).toBeCloseTo(77.6, 2);
  });

  it("haversineMetres returns 0 for same point", () => {
    expect(haversineMetres(12.97, 77.59, 12.97, 77.59)).toBe(0);
  });

  it("haversineMetres returns reasonable distance", () => {
    // ~111 km per degree of latitude
    const dist = haversineMetres(12.97, 77.59, 13.87, 77.59);
    expect(dist).toBeGreaterThan(90_000);
    expect(dist).toBeLessThan(110_000);
  });
});
