import { type FC, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, Cell,
} from "recharts";
import { SectionCard } from "@/components/metrics/MetricCard";
import { LoadingSpinner, ErrorBanner, EmptyState, DisclaimerBanner } from "@/components/feedback/Feedback";
import { useRunEvaluation } from "@/hooks/useApi";
import { formatMetric, formatDuration } from "@/utils/formatting";
import {
  DEMO_HOSPITALS, DEMO_AMBULANCES, DEMO_REQUESTS, DEMO_DISRUPTIONS,
} from "@/utils/demoFixtures";
import type { EvaluationResponse, EvaluationMetric, PolicyResult, ScenarioInput } from "@/types/api";

const BASELINE_COLOR = "#6b7280";
const CASCADEIQ_COLOR = "#3b82f6";

// Build a chart-friendly dataset from two policies
function buildChartData(baseline: PolicyResult, cascadeiq: PolicyResult) {
  const metricMap = new Map<string, { name: string; baseline: number | null; cascadeiq: number | null; unit: string }>();
  for (const m of baseline.metrics) {
    metricMap.set(m.name, { name: m.name, baseline: m.value, cascadeiq: null, unit: m.unit });
  }
  for (const m of cascadeiq.metrics) {
    const existing = metricMap.get(m.name);
    if (existing) existing.cascadeiq = m.value;
    else metricMap.set(m.name, { name: m.name, baseline: null, cascadeiq: m.value, unit: m.unit });
  }
  return Array.from(metricMap.values());
}

// Metric comparison table row
const MetricRow: FC<{ m: EvaluationMetric; compareValue: number | null }> = ({ m, compareValue }) => {
  const improved = compareValue !== null && m.value !== null && m.value < compareValue;
  return (
    <div style={{
      display: "grid", gridTemplateColumns: "1fr auto auto",
      gap: "var(--space-2)", padding: "var(--space-2) 0",
      borderBottom: "1px solid var(--color-border)", alignItems: "start",
    }}>
      <div>
        <div style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--color-text-primary)" }}>
          {m.name.replace(/_/g, " ")}
        </div>
        <div style={{ fontSize: "0.62rem", color: "var(--color-text-muted)", lineHeight: 1.4 }}>{m.explanation}</div>
      </div>
      <div style={{ textAlign: "right", fontFamily: "var(--font-mono)", fontSize: "0.72rem", color: "var(--color-text-primary)" }}>
        {formatMetric(m.value, m.unit)}
      </div>
      {compareValue !== null && m.value !== null && (
        <span style={{
          fontSize: "0.62rem", padding: "1px 5px", borderRadius: "999px",
          background: improved ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.08)",
          color: improved ? "var(--color-success)" : "var(--color-danger)",
          border: `1px solid ${improved ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.25)"}`,
        }}>
          {improved ? "↓ better" : "↑ worse"}
        </span>
      )}
    </div>
  );
};

// Custom tooltip for recharts
const ChartTooltip: FC<{ active?: boolean; payload?: Array<{ name: string; value: number; unit?: string }>; label?: string }> = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: "var(--color-bg-elevated)", border: "1px solid var(--color-border)",
      borderRadius: "var(--radius-md)", padding: "var(--space-2) var(--space-3)",
      fontSize: "0.72rem",
    }}>
      <div style={{ fontWeight: 600, marginBottom: 4, color: "var(--color-text-primary)" }}>
        {String(label).replace(/_/g, " ")}
      </div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.name === "baseline" ? BASELINE_COLOR : CASCADEIQ_COLOR }}>
          {p.name}: {p.value != null ? p.value.toFixed(2) : "—"}
        </div>
      ))}
    </div>
  );
};

interface EvaluationPanelProps {
  demoMode: boolean;
}

const EvaluationPanel: FC<EvaluationPanelProps> = ({ demoMode }) => {
  const mutation = useRunEvaluation();
  const [result, setResult] = useState<EvaluationResponse | null>(null);
  const [lambda, setLambda] = useState(0.3);
  const [mu, setMu] = useState(0.1);

  const buildEvalInput = (): ScenarioInput => ({
    scenario_id: "flood_koramangala_2024",
    seed: 42,
    hospitals: DEMO_HOSPITALS,
    ambulances: DEMO_AMBULANCES,
    emergency_requests: DEMO_REQUESTS,
    road_disruptions: DEMO_DISRUPTIONS,
    simulation_steps: 15,
    weather_mode: "synthetic",
  });

  const handleRun = async () => {
    const data = await mutation.mutateAsync({
      scenario_input: buildEvalInput(),
      objective_lambda: lambda,
      objective_mu: mu,
    });
    setResult(data);
  };

  if (demoMode) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        <EmptyState icon="📊" title="Exit demo mode" message="Evaluation requires the live backend to run both baseline and CascadeIQ simulations." />
      </div>
    );
  }

  const chartData = result ? buildChartData(result.baseline, result.cascadeiq) : [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
      <DisclaimerBanner text="Evaluation compares simulated policies only. Results do not represent real-world performance." />

      <SectionCard title="Comparison Parameters">
        {[
          { id: "eval-lambda", label: `λ (coverage): ${lambda.toFixed(2)}`, val: lambda, set: setLambda },
          { id: "eval-mu", label: `μ (isolation): ${mu.toFixed(2)}`, val: mu, set: setMu },
        ].map(({ id, label, val, set }) => (
          <div key={id} style={{ marginBottom: "var(--space-2)" }}>
            <label htmlFor={id} style={{ fontSize: "0.65rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--color-text-muted)", display: "block", marginBottom: 4 }}>
              {label}
            </label>
            <input id={id} type="range" min={0} max={1} step={0.05} value={val}
              onChange={e => set(parseFloat(e.target.value))}
              style={{ width: "100%", accentColor: "var(--color-accent)" }} />
          </div>
        ))}
        <button
          id="run-evaluation-btn"
          onClick={() => void handleRun()}
          disabled={mutation.isPending}
          style={{
            width: "100%", padding: "var(--space-2)", borderRadius: "var(--radius-md)",
            background: "var(--color-accent)", color: "white", border: "none",
            fontSize: "0.78rem", fontWeight: 600, cursor: "pointer",
            opacity: mutation.isPending ? 0.6 : 1,
          }}
        >
          {mutation.isPending ? "Running evaluation…" : "📊 Run Baseline vs CascadeIQ"}
        </button>
      </SectionCard>

      {mutation.error && <ErrorBanner error={mutation.error} title="Evaluation failed" />}
      {mutation.isPending && <LoadingSpinner label="Running two simulations…" />}

      {result && (
        <>
          {/* Narrative note */}
          <SectionCard title="Summary">
            <p style={{ fontSize: "0.75rem", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>
              {result.comparison_note}
            </p>
          </SectionCard>

          {/* Bar chart */}
          {chartData.length > 0 && (
            <SectionCard title="Metric Comparison Chart">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" horizontal={false} />
                  <XAxis type="number" tick={{ fill: "var(--color-text-muted)", fontSize: 10 }} />
                  <YAxis type="category" dataKey="name" tick={{ fill: "var(--color-text-muted)", fontSize: 9 }}
                    width={120} tickFormatter={v => String(v).replace(/_/g, " ")} />
                  <Tooltip content={<ChartTooltip />} />
                  <Legend wrapperStyle={{ fontSize: "0.7rem", color: "var(--color-text-secondary)" }} />
                  <Bar dataKey="baseline" name="Baseline" fill={BASELINE_COLOR} radius={[0, 3, 3, 0]} />
                  <Bar dataKey="cascadeiq" name="CascadeIQ" fill={CASCADEIQ_COLOR} radius={[0, 3, 3, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </SectionCard>
          )}

          {/* Detailed metric tables */}
          {[
            { policy: result.cascadeiq, compare: result.baseline, title: "CascadeIQ Metrics" },
            { policy: result.baseline, compare: null, title: "Baseline Metrics" },
          ].map(({ policy, compare, title }) => (
            <SectionCard key={policy.policy_name} title={title}>
              {policy.metrics.map(m => (
                <MetricRow
                  key={m.name}
                  m={m}
                  compareValue={compare?.metrics.find(cm => cm.name === m.name)?.value ?? null}
                />
              ))}
            </SectionCard>
          ))}
        </>
      )}
    </div>
  );
};

export default EvaluationPanel;
