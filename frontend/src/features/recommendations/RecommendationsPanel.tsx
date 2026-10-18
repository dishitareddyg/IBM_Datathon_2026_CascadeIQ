import { type FC, useState } from "react";
import { SectionCard } from "@/components/metrics/MetricCard";
import { LoadingSpinner, ErrorBanner, EmptyState, DisclaimerBanner } from "@/components/feedback/Feedback";
import { useRequestRecommendations } from "@/hooks/useApi";
import { formatDuration, formatPercent } from "@/utils/formatting";
import type { InterventionAction, RecommendationResult } from "@/types/api";

const TYPE_COLOUR: Record<string, string> = {
  REROUTE: "var(--color-accent-light)",
  DIVERT: "#f59e0b",
  PREPOSITION: "#22c55e",
};

const InterventionCard: FC<{ action: InterventionAction; rank: number }> = ({ action, rank }) => {
  const [expanded, setExpanded] = useState(false);
  const color = TYPE_COLOUR[action.type] ?? "var(--color-text-muted)";

  return (
    <div style={{
      border: `1px solid ${action.feasible ? "var(--color-border)" : "rgba(239,68,68,0.3)"}`,
      borderRadius: "var(--radius-md)",
      background: action.feasible ? "var(--color-bg-elevated)" : "rgba(239,68,68,0.04)",
      marginBottom: "var(--space-2)",
      overflow: "hidden",
    }}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => setExpanded(p => !p)}
        onKeyDown={e => (e.key === "Enter" || e.key === " ") && setExpanded(p => !p)}
        style={{ padding: "var(--space-3)", cursor: "pointer", display: "flex", gap: "var(--space-2)", alignItems: "flex-start" }}
        aria-expanded={expanded}
      >
        {/* Rank */}
        <span style={{
          width: 22, height: 22, borderRadius: "50%",
          background: action.feasible ? color : "rgba(239,68,68,0.2)",
          color: action.feasible ? "var(--color-bg-base)" : "var(--color-danger)",
          fontSize: "0.65rem", fontWeight: 700,
          display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
        }}>
          {rank}
        </span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center", flexWrap: "wrap", marginBottom: 4 }}>
            <span style={{ fontSize: "0.65rem", fontWeight: 700, color, textTransform: "uppercase", letterSpacing: "0.04em" }}>
              {action.type}
            </span>
            {!action.feasible && (
              <span style={{ fontSize: "0.6rem", color: "var(--color-danger)", fontWeight: 600 }}>INFEASIBLE</span>
            )}
            {action.objective_score != null && (
              <span style={{ fontSize: "0.62rem", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
                score: {action.objective_score.toFixed(2)}
              </span>
            )}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)", lineHeight: 1.4 }}>
            {action.description}
          </div>
        </div>
        <span style={{ fontSize: "0.65rem", color: "var(--color-text-muted)", flexShrink: 0 }}>
          {expanded ? "▲" : "▼"}
        </span>
      </div>

      {expanded && (
        <div style={{ padding: "0 var(--space-3) var(--space-3)", borderTop: "1px solid var(--color-border)" }}>
          <div style={{ paddingTop: "var(--space-2)", display: "flex", flexDirection: "column", gap: 4 }}>
            {action.target_ambulance_id && (
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem" }}>
                <span style={{ color: "var(--color-text-muted)" }}>Ambulance</span>
                <span style={{ fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>{action.target_ambulance_id}</span>
              </div>
            )}
            {action.target_request_id && (
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem" }}>
                <span style={{ color: "var(--color-text-muted)" }}>Request</span>
                <span style={{ fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>{action.target_request_id}</span>
              </div>
            )}
            {action.target_hospital_id && (
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem" }}>
                <span style={{ color: "var(--color-text-muted)" }}>Hospital</span>
                <span style={{ fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>{action.target_hospital_id}</span>
              </div>
            )}
            {action.response_time_s != null && (
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem" }}>
                <span style={{ color: "var(--color-text-muted)" }}>Est. response time</span>
                <span style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent-light)" }}>{formatDuration(action.response_time_s)}</span>
              </div>
            )}
            {action.new_route && (
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.72rem" }}>
                <span style={{ color: "var(--color-text-muted)" }}>Route feasible</span>
                <span style={{ color: action.new_route.is_feasible ? "var(--color-success)" : "var(--color-danger)" }}>
                  {action.new_route.is_feasible ? "Yes" : "No"}
                </span>
              </div>
            )}
            {!action.feasible && action.infeasibility_reason && (
              <div style={{
                marginTop: "var(--space-1)", padding: "var(--space-2)", borderRadius: "var(--radius-sm)",
                background: "rgba(239,68,68,0.07)", border: "1px solid rgba(239,68,68,0.2)",
                fontSize: "0.7rem", color: "rgba(239,68,68,0.85)", lineHeight: 1.4,
              }}>
                <strong>Infeasible:</strong> {action.infeasibility_reason}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

interface RecommendationsPanelProps {
  simulationId: string | null;
}

const RecommendationsPanel: FC<RecommendationsPanelProps> = ({ simulationId }) => {
  const mutation = useRequestRecommendations();
  const [result, setResult] = useState<RecommendationResult | null>(null);
  const [lambda, setLambda] = useState(0.3);
  const [mu, setMu] = useState(0.1);
  const [maxRecs, setMaxRecs] = useState(5);

  if (!simulationId) {
    return <EmptyState icon="💡" title="No simulation yet" message="Run a simulation to generate intervention recommendations." />;
  }

  const handleGenerate = async () => {
    const data = await mutation.mutateAsync({ simulation_id: simulationId, objective_lambda: lambda, objective_mu: mu, max_recommendations: maxRecs });
    setResult(data);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      <DisclaimerBanner text="Recommendations are simulated decision support, not verified operational instructions." />

      {/* Parameters */}
      <SectionCard title="Objective Parameters">
        {[
          { id: "rec-lambda", label: `λ (coverage weight): ${lambda.toFixed(2)}`, val: lambda, set: setLambda },
          { id: "rec-mu", label: `μ (isolation penalty): ${mu.toFixed(2)}`, val: mu, set: setMu },
        ].map(({ id, label, val, set }) => (
          <div key={id} style={{ marginBottom: "var(--space-2)" }}>
            <label htmlFor={id} style={{ fontSize: "0.65rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-text-muted)", display: "block", marginBottom: 4 }}>
              {label}
            </label>
            <input
              id={id}
              type="range" min={0} max={1} step={0.05}
              value={val}
              onChange={e => set(parseFloat(e.target.value))}
              style={{ width: "100%", accentColor: "var(--color-accent)" }}
            />
          </div>
        ))}
        <div style={{ marginBottom: "var(--space-2)" }}>
          <label htmlFor="rec-max" style={{ fontSize: "0.65rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-text-muted)", display: "block", marginBottom: 4 }}>
            Max recommendations: {maxRecs}
          </label>
          <input id="rec-max" type="range" min={1} max={10} step={1} value={maxRecs} onChange={e => setMaxRecs(parseInt(e.target.value))}
            style={{ width: "100%", accentColor: "var(--color-accent)" }} />
        </div>
        <button
          id="generate-recommendations-btn"
          onClick={() => void handleGenerate()}
          disabled={mutation.isPending}
          style={{
            width: "100%", padding: "var(--space-2)", borderRadius: "var(--radius-md)",
            background: "var(--color-accent)", color: "white", border: "none",
            fontSize: "0.78rem", fontWeight: 600, cursor: "pointer",
            opacity: mutation.isPending ? 0.6 : 1,
          }}
        >
          {mutation.isPending ? "Generating…" : "💡 Generate Recommendations"}
        </button>
      </SectionCard>

      {mutation.error && <ErrorBanner error={mutation.error} title="Failed to get recommendations" />}

      {result && (
        <SectionCard title={`Interventions — ${result.ranked_interventions.length} ranked`}>
          <div style={{ fontSize: "0.65rem", color: "var(--color-text-muted)", marginBottom: "var(--space-2)" }}>
            Method: {result.method_note} · Latency: {result.computation_latency_ms.toFixed(0)} ms
          </div>
          {result.ranked_interventions.length === 0
            ? <EmptyState icon="—" title="No interventions" message="No feasible interventions found for this simulation state." />
            : result.ranked_interventions.map((action, i) => (
                <InterventionCard key={action.action_id} action={action} rank={i + 1} />
              ))
          }
        </SectionCard>
      )}
    </div>
  );
};

export default RecommendationsPanel;
