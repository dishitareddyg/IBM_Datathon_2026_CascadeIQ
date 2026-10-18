import { type FC, useState, useCallback } from "react";
import { useScenarios, useRunSimulation } from "@/hooks/useApi";
import {
  LoadingSpinner,
  ErrorBanner,
  DisclaimerBanner,
} from "@/components/feedback/Feedback";
import { SectionCard } from "@/components/metrics/MetricCard";
import type {
  ScenarioConfig,
  ScenarioInput,
  WeatherMode,
  SimulationResult,
} from "@/types/api";
import {
  DEMO_HOSPITALS,
  DEMO_AMBULANCES,
  DEMO_REQUESTS,
  DEMO_DISRUPTIONS,
  DEMO_SCENARIOS,
} from "@/utils/demoFixtures";
import styles from "./SimulationControls.module.css";

interface SimulationControlsProps {
  demoMode: boolean;
  onSimulationComplete: (result: SimulationResult) => void;
}

const SimulationControls: FC<SimulationControlsProps> = ({
  demoMode,
  onSimulationComplete,
}) => {
  const { data: apiScenarios, isLoading: scenariosLoading, error: scenariosError } =
    useScenarios();
  const scenarios = demoMode ? DEMO_SCENARIOS : (apiScenarios ?? []);

  const [selectedScenario, setSelectedScenario] = useState<ScenarioConfig | null>(null);
  const [weatherMode, setWeatherMode] = useState<WeatherMode>("synthetic");
  const [seed, setSeed] = useState(42);
  const [steps, setSteps] = useState(10);
  const [lastInput, setLastInput] = useState<ScenarioInput | null>(null);

  const runMutation = useRunSimulation();

  const buildInput = useCallback(
    (scenario: ScenarioConfig, s: number, wm: WeatherMode, st: number): ScenarioInput => ({
      scenario_id: scenario.scenario_id,
      seed: s,
      hospitals: DEMO_HOSPITALS,
      ambulances: DEMO_AMBULANCES,
      emergency_requests: DEMO_REQUESTS,
      road_disruptions: DEMO_DISRUPTIONS,
      simulation_steps: st,
      weather_mode: wm,
    }),
    [],
  );

  const handleRun = useCallback(async () => {
    if (!selectedScenario) return;
    const input = buildInput(selectedScenario, seed, weatherMode, steps);
    setLastInput(input);
    try {
      const result = await runMutation.mutateAsync(input);
      onSimulationComplete(result);
    } catch {
      // Error shown via runMutation.error
    }
  }, [selectedScenario, seed, weatherMode, steps, buildInput, runMutation, onSimulationComplete]);

  const handleRerun = useCallback(async () => {
    if (!lastInput) return;
    try {
      const result = await runMutation.mutateAsync(lastInput);
      onSimulationComplete(result);
    } catch {
      // Error shown via runMutation.error
    }
  }, [lastInput, runMutation, onSimulationComplete]);

  const handleReset = useCallback(() => {
    setSelectedScenario(null);
    setSeed(42);
    setSteps(10);
    setWeatherMode("synthetic");
    setLastInput(null);
    runMutation.reset();
  }, [runMutation]);

  if (scenariosLoading && !demoMode) return <LoadingSpinner label="Loading scenarios…" />;

  return (
    <div className={styles.controls}>
      {/* Scenario selection */}
      <SectionCard title="Scenario">
        {scenariosError && !demoMode && (
          <ErrorBanner error={scenariosError} title="Could not load scenarios" />
        )}
        {scenarios.map((sc) => (
          <div
            key={sc.scenario_id}
            id={`scenario-card-${sc.scenario_id}`}
            className={`${styles["scenario-card"]} ${selectedScenario?.scenario_id === sc.scenario_id ? styles["scenario-card--selected"] : ""}`}
            onClick={() => {
              setSelectedScenario(sc);
              setSteps(sc.default_simulation_steps);
              setWeatherMode(sc.weather_mode);
            }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                setSelectedScenario(sc);
                setSteps(sc.default_simulation_steps);
              }
            }}
            aria-pressed={selectedScenario?.scenario_id === sc.scenario_id}
          >
            <div className={styles["scenario-card__name"]}>{sc.display_name}</div>
            <div className={styles["scenario-card__desc"]}>{sc.description}</div>
            <div className={styles["scenario-card__tags"]}>
              {sc.tags.map((tag) => (
                <span key={tag} className={styles["scenario-tag"]}>{tag}</span>
              ))}
            </div>
          </div>
        ))}
      </SectionCard>

      {/* Parameters */}
      <SectionCard title="Parameters">
        {/* Weather mode */}
        <div className={styles["form-group"]}>
          <label className={styles["form-label"]}>Weather mode</label>
          <div className={styles["mode-toggle"]}>
            {(["synthetic", "historical", "live"] as WeatherMode[]).map((mode) => (
              <button
                key={mode}
                id={`weather-mode-${mode}`}
                className={`${styles["mode-btn"]} ${weatherMode === mode ? styles["mode-btn--active"] : ""}`}
                onClick={() => setWeatherMode(mode)}
                title={
                  mode === "live"
                    ? "Requires IMD_API_KEY in backend environment"
                    : undefined
                }
              >
                {mode}
              </button>
            ))}
          </div>
          {weatherMode === "live" && (
            <span className={styles["form-hint"]}>
              ⚠ Live mode requires a valid IMD_API_KEY on the backend.
            </span>
          )}
        </div>

        {/* Seed */}
        <div className={styles["form-group"]}>
          <label htmlFor="sim-seed" className={styles["form-label"]}>
            Random seed
          </label>
          <input
            id="sim-seed"
            type="number"
            className={styles["form-input"]}
            value={seed}
            onChange={(e) => setSeed(parseInt(e.target.value, 10) || 0)}
            min={0}
            max={99999}
          />
          <span className={styles["form-hint"]}>
            Same seed + scenario = reproducible results.
          </span>
        </div>

        {/* Steps */}
        <div className={styles["form-group"]}>
          <label htmlFor="sim-steps" className={styles["form-label"]}>
            Simulation steps: <span style={{ color: "var(--color-accent-light)" }}>{steps}</span>
            <span style={{ fontSize: "0.6rem", marginLeft: 4 }}>
              ({steps * 5} sim-minutes)
            </span>
          </label>
          <div className={styles["range-row"]}>
            <input
              id="sim-steps"
              type="range"
              className={styles["form-input"]}
              value={steps}
              onChange={(e) => setSteps(parseInt(e.target.value, 10))}
              min={1}
              max={50}
            />
            <span className={styles["range-value"]}>{steps}</span>
          </div>
        </div>
      </SectionCard>

      {/* Run error */}
      {runMutation.error && (
        <ErrorBanner error={runMutation.error} title="Simulation failed" />
      )}

      {/* Action buttons */}
      <div className={styles["btn-group"]}>
        <button
          id="run-simulation-btn"
          className={`${styles.btn} ${styles["btn--primary"]}`}
          onClick={() => void handleRun()}
          disabled={!selectedScenario || runMutation.isPending || demoMode}
          title={demoMode ? "Disable demo mode to run a live simulation" : undefined}
        >
          {runMutation.isPending ? (
            <>
              <div className={styles["btn-spinner"]} aria-hidden="true" />
              Running…
            </>
          ) : (
            "▶ Run"
          )}
        </button>
        <button
          id="rerun-simulation-btn"
          className={`${styles.btn} ${styles["btn--secondary"]}`}
          onClick={() => void handleRerun()}
          disabled={!lastInput || runMutation.isPending || demoMode}
          title="Rerun with the exact same seed and parameters"
        >
          ↺ Rerun
        </button>
        <button
          id="reset-simulation-btn"
          className={`${styles.btn} ${styles["btn--secondary"]}`}
          onClick={handleReset}
          disabled={runMutation.isPending}
        >
          ⊘ Reset
        </button>
      </div>

      {demoMode && (
        <p style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", textAlign: "center" }}>
          Exit demo mode to send simulation requests to the backend.
        </p>
      )}

      <DisclaimerBanner text="Results are computer-generated estimates. Do not use for real emergency management decisions." />
    </div>
  );
};

export default SimulationControls;
