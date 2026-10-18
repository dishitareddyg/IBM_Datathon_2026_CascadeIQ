/**
 * Geographic utilities for the CascadeIQ map layer.
 */
import type { BoundingBox } from "@/types/api";

/** Bengaluru Urban district approximate bounding box */
export const BLR_BBOX: BoundingBox = {
  min_lat: 12.75,
  min_lon: 77.35,
  max_lat: 13.18,
  max_lon: 77.85,
};

/** Approximate centre of Bengaluru Urban */
export const BLR_CENTRE: [number, number] = [12.9716, 77.5946];

/** Convert a BoundingBox to Leaflet LatLngBounds array format [[sw], [ne]] */
export function bboxToLeafletBounds(
  bbox: BoundingBox,
): [[number, number], [number, number]] {
  return [
    [bbox.min_lat, bbox.min_lon],
    [bbox.max_lat, bbox.max_lon],
  ];
}

/** Compute bounding box centre */
export function bboxCentre(bbox: BoundingBox): [number, number] {
  return [
    (bbox.min_lat + bbox.max_lat) / 2,
    (bbox.min_lon + bbox.max_lon) / 2,
  ];
}

/** Haversine distance between two lat/lon points (metres) */
export function haversineMetres(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const R = 6_371_000;
  const φ1 = (lat1 * Math.PI) / 180;
  const φ2 = (lat2 * Math.PI) / 180;
  const Δφ = ((lat2 - lat1) * Math.PI) / 180;
  const Δλ = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(Δφ / 2) ** 2 +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/** Colours for road status */
export const ROAD_STATUS_COLOUR: Record<string, string> = {
  OPEN: "#22c55e",      // green-500
  DEGRADED: "#f59e0b",  // amber-500
  CLOSED: "#ef4444",    // red-500
};

/** Colours for warning severity */
export const WARNING_SEVERITY_COLOUR: Record<string, string> = {
  WATCH: "#3b82f6",     // blue-500
  WARNING: "#f59e0b",   // amber-500
  SEVERE: "#ef4444",    // red-500
  EXTREME: "#7c3aed",   // violet-600
};
