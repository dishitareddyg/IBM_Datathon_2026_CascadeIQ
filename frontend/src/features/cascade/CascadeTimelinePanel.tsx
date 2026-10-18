import { type FC, useState } from "react";
import { SectionCard } from "@/components/metrics/MetricCard";
import { LoadingSpinner, ErrorBanner, EmptyState, DisclaimerBanner } from "@/components/feedback/Feedback";
import { useCascade } from "@/hooks/useApi";
import { formatDateTime, formatDuration } from "@/utils/formatting";
import type { CascadeStep, CascadeEventSchema } from "@/types/api";

// Colour by event type
const EVENT_COLOURS: Record<string, string> = {
  ROAD_DEGRADED: "var(--color-warning)",
  ROAD_CLOSED: "var(--color-danger)",
  HOSPITAL_OVERLOADED: "#f97316",
  REQUEST_UNREACHABLE: "var(--color-danger)",
  FACILITY_ISOLATED: "#7c3aed",
  ASSIGNMENT: "var(--color-success)",
};

const EventRow: FC<{ event: CascadeEventSchema }> = ({ event }) => {
  const color = EVENT_COLOURS[event.event_type] ?? "var(--color-text-muted)";
  return (
    <div style={{
      display: "flex", gap: "var(--space-2)", padding: "var(--space-2) 0",
      borderBottom: "1px solid var(--color-border)", alignItems: "flex-start",
    }}>
      <span style={{
        width: 8, height: 8, borderRadius: "50%", background: color,
        flexShrink: 0, marginTop: 5,
      }} aria-hidden="true" />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontSize: "0.65rem", fontWeight: 700, color, textTransform: "uppercase", letterSpacing: "0.04em" }}>
            {event.event_type.replace(/_/g, " ")}
          </span>
          <span style={{ fontSize: "0.62rem", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
            {event.affected_entity_id}
          </span>
          <span style={{
            fontSize: "0.6rem", padding: "1px 5px", borderRadius: "999px",
            background: "var(--color-bg-hover)", color: "var(--color-text-muted)",
            border: "1px solid var(--color-border)",
          }}>
            {event.provenance}
          </span>
        </div>
        <div style={{ fontSize: "0.72rem", color: "var(--color-text-secondary)", marginTop: 2, lineHeight: 1.4 }}>
          {event.description}
        </div>
        <div style={{ fontSize: "0.62rem", color: "var(--color-text-muted)", marginTop: 2 }}>
          Severity: {(event.severity * 100).toFixed(0)}%
        </div>
      </div>
    </div>
  );
};

const StepCard: FC<{ step: CascadeStep; isSelected: boolean; onClick: () => void }> = ({ step, isSelected, onClick }) => {
  const hasEvents = step.cascade_events.length > 0;
  const hasDisruptions = step.active_disruptions.length > 0;
  const hasUnreachable = step.unreachable_requests.length > 0;

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={e => (e.key === "Enter" || e.key === " ") && onClick()}
      style={{
        padding: "var(--space-2) var(--space-3)",
        background: isSelected ? "rgba(59,130,246,0.08)" : "var(--color-bg-elevated)",
        border: `1px solid ${isSelected ? "var(--color-accent)" : "var(--color-border)"}`,
        borderRadius: "var(--radius-md)",
        cursor: "pointer",
        transition: "all 120ms ease",
        marginBottom: "var(--space-1)",
      }}
      aria-pressed={isSelected}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-2)" }}>
        <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--color-text-primary)", fontFamily: "var(--font-mono)" }}>
          Step {step.step_index}
        </span>
        <span style={{ fontSize: "0.62rem", color: "var(--color-text-muted)" }}>
          {formatDateTime(step.timestamp)}
        </span>
      </div>
      <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-1)", flexWrap: "wrap" }}>
        {hasDisruptions && (
          <span style={{ fontSize: "0.62rem", color: "var(--color-warning)" }}>
            ⚠ {step.active_disruptions.length} disrupted
          </span>
        )}
        {hasUnreachable && (
          <span style={{ fontSize: "0.62rem", color: "var(--color-danger)" }}>
            ✕ {step.unreachable_requests.length} unreachable
          </span>
        )}
        {step.isolated_facilities.length > 0 && (
          <span style={{ fontSize: "0.62rem", color: "#7c3aed" }}>
            ⊗ {step.isolated_facilities.length} isolated
          </span>
        )}
        {!hasEvents && !hasDisruptions && !hasUnreachable && (
          <span style={{ fontSize: "0.62rem", color: "var(--color-success)" }}>✓ Stable</span>
        )}
      </div>
    </div>
  );
};

interface CascadeTimelinePanelProps {
  simulationId: string | null;
}

const CascadeTimelinePanel: FC<CascadeTimelinePanelProps> = ({ simulationId }) => {
  const { data: steps, isLoading, error } = useCascade(simulationId);
  const [selectedStep, setSelectedStep] = useState<number | null>(null);

  if (!simulationId) {
    return <EmptyState icon="⏱" title="No simulation yet" message="Run a simulation to see the cascade timeline." />;
  }
  if (isLoading) return <LoadingSpinner label="Loading cascade…" />;
  if (error) return <ErrorBanner error={error} title="Could not load cascade" />;
  if (!steps || steps.length === 0) return <EmptyState icon="⏱" title="No steps" message="The simulation produced no timeline steps." />;

  const active = selectedStep !== null ? steps.find(s => s.step_index === selectedStep) : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      <DisclaimerBanner text="Cascade timeline is simulated, not an incident log." />

      <SectionCard title={`Timeline — ${steps.length} steps`}>
        <div style={{ maxHeight: 280, overflowY: "auto", paddingRight: 4 }}>
          {steps.map(step => (
            <StepCard
              key={step.step_index}
              step={step}
              isSelected={selectedStep === step.step_index}
              onClick={() => setSelectedStep(prev => prev === step.step_index ? null : step.step_index)}
            />
          ))}
        </div>
      </SectionCard>

      {active && (
        <SectionCard title={`Step ${active.step_index} — Events`}>
          {active.cascade_events.length === 0 ? (
            <p style={{ fontSize: "0.72rem", color: "var(--color-text-muted)" }}>No notable events this step.</p>
          ) : (
            active.cascade_events.map((ev, i) => <EventRow key={i} event={ev} />)
          )}

          {/* Hospital loads */}
          {Object.keys(active.hospital_loads).length > 0 && (
            <div style={{ marginTop: "var(--space-2)" }}>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-text-muted)", marginBottom: "var(--space-1)" }}>
                Hospital occupancy
              </div>
              {Object.entries(active.hospital_loads).map(([id, load]) => (
                <div key={id} style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", marginBottom: 4 }}>
                  <span style={{ fontSize: "0.7rem", color: "var(--color-text-secondary)", minWidth: 60 }}>{id}</span>
                  <div style={{ flex: 1, height: 6, background: "var(--color-bg-base)", borderRadius: 3, overflow: "hidden" }}>
                    <div style={{
                      height: "100%", width: `${Math.min(load * 100, 100)}%`,
                      background: load > 1 ? "var(--color-danger)" : load > 0.8 ? "var(--color-warning)" : "var(--color-success)",
                      borderRadius: 3, transition: "width 300ms ease",
                    }} />
                  </div>
                  <span style={{ fontSize: "0.65rem", fontFamily: "var(--font-mono)", color: load > 1 ? "var(--color-danger)" : "var(--color-text-muted)", minWidth: 32 }}>
                    {(load * 100).toFixed(0)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      )}
    </div>
  );
};

export default CascadeTimelinePanel;
