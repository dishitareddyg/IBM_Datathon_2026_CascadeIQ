import { type FC } from "react";
import { useWeatherStatus } from "@/hooks/useApi";
import { SectionCard, StatusRow, SourceBadge } from "@/components/metrics/MetricCard";
import {
  LoadingSpinner,
  ErrorBanner,
  DisclaimerBanner,
  StaleBadge,
} from "@/components/feedback/Feedback";
import {
  formatDateTime,
  formatAge,
  formatRainfall,
} from "@/utils/formatting";
import { WARNING_SEVERITY_COLOUR } from "@/utils/geo";
import type { WeatherStatus, WeatherWarning, RainfallObservation } from "@/types/api";

interface WeatherPanelProps {
  seed: number;
  demoData?: WeatherStatus | null;
}

// ── Warning card ───────────────────────────────────────────────────────────────

const WarningCard: FC<{ warning: WeatherWarning }> = ({ warning }) => {
  const color = WARNING_SEVERITY_COLOUR[warning.severity] ?? "#6b7280";
  const isExpired = new Date(warning.valid_until) < new Date();

  return (
    <div
      style={{
        border: `1px solid ${color}44`,
        borderLeft: `3px solid ${color}`,
        background: `${color}08`,
        borderRadius: "var(--radius-md)",
        padding: "var(--space-3)",
        marginBottom: "var(--space-2)",
        opacity: isExpired ? 0.5 : 1,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-2)",
          marginBottom: "var(--space-1)",
        }}
      >
        <span
          style={{
            fontSize: "0.65rem",
            fontWeight: 700,
            color,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
          }}
        >
          {warning.severity}
        </span>
        <span
          style={{
            fontSize: "0.7rem",
            fontWeight: 600,
            color: "var(--color-text-secondary)",
          }}
        >
          {warning.warning_type.replace(/_/g, " ")}
        </span>
        <SourceBadge source={warning.source} />
        {isExpired && (
          <span style={{ fontSize: "0.6rem", color: "var(--color-text-muted)" }}>
            EXPIRED
          </span>
        )}
      </div>
      <p
        style={{
          fontSize: "0.72rem",
          color: "var(--color-text-secondary)",
          lineHeight: 1.5,
          marginBottom: "var(--space-1)",
        }}
      >
        {warning.description}
      </p>
      <div
        style={{
          display: "flex",
          gap: "var(--space-3)",
          fontSize: "0.65rem",
          color: "var(--color-text-muted)",
        }}
      >
        <span>Issued: {formatDateTime(warning.issued_at)}</span>
        <span>Valid until: {formatDateTime(warning.valid_until)}</span>
      </div>
    </div>
  );
};

// ── Observation row ────────────────────────────────────────────────────────────

const ObsRow: FC<{ obs: RainfallObservation }> = ({ obs }) => (
  <div
    style={{
      display: "grid",
      gridTemplateColumns: "1fr auto auto",
      gap: "var(--space-2)",
      alignItems: "center",
      padding: "var(--space-1) 0",
      borderBottom: "1px solid var(--color-border)",
      fontSize: "0.72rem",
    }}
  >
    <div>
      <div style={{ fontWeight: 600, color: "var(--color-text-primary)" }}>
        {obs.station_id}
      </div>
      <div style={{ color: "var(--color-text-muted)", fontSize: "0.62rem" }}>
        {obs.lat.toFixed(3)}°N {obs.lon.toFixed(3)}°E
      </div>
    </div>
    <div style={{ textAlign: "right" }}>
      <div style={{ fontWeight: 600, color: "var(--color-accent-light)", fontFamily: "var(--font-mono)" }}>
        {formatRainfall(obs.rainfall_mm_1h)} /1h
      </div>
      <div style={{ color: "var(--color-text-muted)", fontFamily: "var(--font-mono)", fontSize: "0.65rem" }}>
        {formatRainfall(obs.rainfall_mm_24h)} /24h
      </div>
    </div>
    <SourceBadge source={obs.source} />
  </div>
);

// ── Main WeatherPanel ──────────────────────────────────────────────────────────

const WeatherPanel: FC<WeatherPanelProps> = ({ seed, demoData }) => {
  const { data: apiData, isLoading, error } = useWeatherStatus(seed);
  const data = demoData ?? apiData;

  if (isLoading && !demoData) return <LoadingSpinner label="Loading weather…" />;

  if (error && !demoData) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        <ErrorBanner error={error} title="Weather data unavailable" />
        <SectionCard title="Weather Status">
          <p style={{ fontSize: "0.72rem", color: "var(--color-text-muted)" }}>
            Could not retrieve weather data from the backend. The backend may be
            offline or the weather service may be unavailable.
          </p>
        </SectionCard>
      </div>
    );
  }

  if (!data) return null;

  const ageMs = Date.now() - new Date(data.data_freshness).getTime();
  const isStale = ageMs > 30 * 60 * 1000; // stale after 30 min

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      <DisclaimerBanner text={data.disclaimer} />

      {/* Active warnings */}
      <SectionCard
        title="Active Warnings"
        badge={
          <span
            style={{
              fontSize: "0.65rem",
              fontWeight: 600,
              padding: "1px 6px",
              borderRadius: "999px",
              background: data.active_warnings.length > 0 ? "rgba(239,68,68,0.12)" : "rgba(74,96,128,0.1)",
              color: data.active_warnings.length > 0 ? "var(--color-danger)" : "var(--color-text-muted)",
            }}
          >
            {data.active_warnings.length}
          </span>
        }
      >
        {data.active_warnings.length === 0 ? (
          <p style={{ fontSize: "0.72rem", color: "var(--color-text-muted)" }}>
            No active warnings.
          </p>
        ) : (
          data.active_warnings.map((w) => (
            <WarningCard key={w.warning_id} warning={w} />
          ))
        )}
      </SectionCard>

      {/* Rainfall observations */}
      <SectionCard
        title="Rainfall Observations"
        badge={isStale ? <StaleBadge age={formatAge(data.data_freshness)} /> : undefined}
      >
        <StatusRow label="Freshness" value={formatAge(data.data_freshness)} />
        {data.current_observations.map((obs) => (
          <ObsRow key={obs.station_id} obs={obs} />
        ))}
        {data.current_observations.length === 0 && (
          <p style={{ fontSize: "0.72rem", color: "var(--color-text-muted)" }}>
            No observations available.
          </p>
        )}
      </SectionCard>
    </div>
  );
};

export default WeatherPanel;
