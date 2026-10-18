import { type FC } from "react";
import { useCityMetadata, useHealth, useSimulation } from "@/hooks/useApi";
import { KpiCard, KpiGrid, SectionCard, StatusRow } from "@/components/metrics/MetricCard";
import { LoadingSpinner, ErrorBanner, DisclaimerBanner } from "@/components/feedback/Feedback";
import { formatDateTime, formatDuration } from "@/utils/formatting";
import type { SimulationResult } from "@/types/api";

interface OverviewPanelProps {
  simulation: SimulationResult | null;
  simulationLoading: boolean;
}

const OverviewPanel: FC<OverviewPanelProps> = ({ simulation, simulationLoading }) => {
  const { data: meta, isLoading: metaLoading, error: metaError } = useCityMetadata();
  const { data: health } = useHealth();

  // Derive KPI values from simulation
  const lastStep = simulation?.steps[simulation.steps.length - 1];
  const affectedRoads = lastStep?.active_disruptions.length ?? 0;
  const unreachableReqs = lastStep?.unreachable_requests.length ?? 0;
  const isolatedFacilities = lastStep?.isolated_facilities.length ?? 0;

  // Mean response time from final assignments
  const responseTimes = simulation?.final_assignments
    .map((a) => a.estimated_arrival_s)
    .filter((t) => t > 0) ?? [];
  const meanResponseTime =
    responseTimes.length > 0
      ? responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length
      : null;

  if (metaLoading) return <LoadingSpinner label="Loading city data…" />;
  if (metaError) return <ErrorBanner error={metaError} title="City data unavailable" />;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      {/* Study area info */}
      <SectionCard title="Study Area">
        {meta && (
          <>
            <StatusRow label="District" value={meta.district} />
            <StatusRow label="State" value={meta.state} />
            <StatusRow label="Area" value={`${meta.area_km2.toLocaleString()} km²`} />
            <StatusRow
              label="Population"
              value={`~${(meta.population_approx / 1_000_000).toFixed(1)}M`}
            />
            <StatusRow
              label="Data sources"
              value={meta.data_sources.join(", ")}
            />
          </>
        )}
      </SectionCard>

      {/* Backend status */}
      <SectionCard title="System Status">
        <StatusRow
          label="Backend"
          value={
            health
              ? <span style={{ color: "var(--color-success)" }}>Online v{health.version}</span>
              : <span style={{ color: "var(--color-danger)" }}>Unavailable</span>
          }
        />
        <StatusRow
          label="Road graph"
          value={
            health?.graph_loaded
              ? <span style={{ color: "var(--color-success)" }}>Loaded</span>
              : <span style={{ color: "var(--color-warning)" }}>Not loaded</span>
          }
        />
        <StatusRow
          label="Last refresh"
          value={formatDateTime(new Date().toISOString())}
        />
      </SectionCard>

      {/* KPI cards — only shown after a simulation */}
      <SectionCard
        title="Simulation KPIs"
        badge={
          simulation
            ? <span style={{ color: "var(--color-accent-light)", fontSize: "0.65rem", fontWeight: 600 }}>
                SIMULATED
              </span>
            : null
        }
      >
        {simulationLoading && <LoadingSpinner label="Running simulation…" />}
        {!simulation && !simulationLoading && (
          <p style={{ fontSize: "0.72rem", color: "var(--color-text-muted)", padding: "var(--space-2) 0" }}>
            Run a simulation to see KPI metrics here.
          </p>
        )}
        {simulation && (
          <>
            <KpiGrid>
              <KpiCard
                id="kpi-affected-roads"
                label="Affected roads"
                value={affectedRoads}
                variant={affectedRoads > 10 ? "alert" : affectedRoads > 4 ? "warning" : "normal"}
                sub="segments disrupted"
              />
              <KpiCard
                id="kpi-unreachable"
                label="Unreachable"
                value={unreachableReqs}
                variant={unreachableReqs > 0 ? "alert" : "normal"}
                sub="emergency requests"
              />
              <KpiCard
                id="kpi-isolated"
                label="Isolated"
                value={isolatedFacilities}
                variant={isolatedFacilities > 0 ? "alert" : "normal"}
                sub="facilities"
              />
              <KpiCard
                id="kpi-response-time"
                label="Mean ETA"
                value={meanResponseTime != null ? formatDuration(meanResponseTime) : "—"}
                sub="estimated arrival"
              />
            </KpiGrid>
            <DisclaimerBanner text={simulation.disclaimer} />
          </>
        )}
      </SectionCard>

      {meta && (
        <p style={{ fontSize: "0.62rem", color: "var(--color-text-muted)", lineHeight: 1.5 }}>
          {meta.boundary_note}
        </p>
      )}
    </div>
  );
};

export default OverviewPanel;
