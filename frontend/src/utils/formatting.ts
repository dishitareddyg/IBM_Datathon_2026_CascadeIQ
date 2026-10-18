/**
 * Formatting utilities for the CascadeIQ dashboard.
 */

/** Format seconds into a human-readable string like "4m 30s" */
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return "—";
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return rem === 0 ? `${m}m` : `${m}m ${rem}s`;
}

/** Format metres into km with 1 decimal if ≥ 1000 m */
export function formatDistance(metres: number | null | undefined): string {
  if (metres == null) return "—";
  if (metres >= 1000) return `${(metres / 1000).toFixed(1)} km`;
  return `${Math.round(metres)} m`;
}

/** Format a ratio [0,1] as a percentage string like "75%" */
export function formatPercent(ratio: number | null | undefined, decimals = 0): string {
  if (ratio == null) return "—";
  return `${(ratio * 100).toFixed(decimals)}%`;
}

/** Format a timestamp ISO string to locale date+time */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

/** Format a timestamp to just time */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString("en-IN", {
      timeZone: "Asia/Kolkata",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}

/** How stale is this timestamp? Returns a human-readable "X ago" string */
export function formatAge(iso: string | null | undefined): string {
  if (!iso) return "unknown";
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 0) return "just now";
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return `${h}h ago`;
}

/** Clamp a number between min and max */
export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/** Format rainfall mm with unit */
export function formatRainfall(mm: number | null | undefined): string {
  if (mm == null) return "—";
  return `${mm.toFixed(1)} mm`;
}

/** Format flood risk as Low/Moderate/High/Critical */
export function formatFloodRisk(risk: number): string {
  if (risk < 0.25) return "Low";
  if (risk < 0.5) return "Moderate";
  if (risk < 0.75) return "High";
  return "Critical";
}

/** Format a metric value with its unit */
export function formatMetric(
  value: number | null | undefined,
  unit: string,
): string {
  if (value == null) return "—";
  if (unit === "seconds") return formatDuration(value);
  if (unit === "ratio") return formatPercent(value, 1);
  if (unit === "%") return `${value.toFixed(1)}%`;
  if (unit === "count") return String(Math.round(value));
  return `${value.toFixed(2)} ${unit}`;
}
