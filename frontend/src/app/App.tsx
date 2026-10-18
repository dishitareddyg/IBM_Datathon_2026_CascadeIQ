import { useState, useCallback } from "react";
import TopBar from "@/components/layout/TopBar";
import CityMap from "@/components/map/CityMap";
import OverviewPanel from "@/features/overview/OverviewPanel";
import WeatherPanel from "@/features/weather/WeatherPanel";
import SimulationControls from "@/features/simulations/SimulationControls";
import CascadeTimelinePanel from "@/features/cascade/CascadeTimelinePanel";
import RecommendationsPanel from "@/features/recommendations/RecommendationsPanel";
import EvaluationPanel from "@/features/evaluation/EvaluationPanel";
import { useCityGraph } from "@/hooks/useApi";
import { DemoBanner } from "@/components/feedback/Feedback";
import { DEMO_WEATHER_STATUS } from "@/utils/demoFixtures";
import type { SimulationResult } from "@/types/api";
import styles from "./App.module.css";

// Sidebar tabs
const SIDEBAR_TABS = [
  { id: "overview", label: "Overview" },
  { id: "weather", label: "Weather" },
  { id: "simulate", label: "Simulate" },
] as const;
type SidebarTab = (typeof SIDEBAR_TABS)[number]["id"];

// Right panel tabs
const PANEL_TABS = [
  { id: "cascade", label: "Cascade" },
  { id: "recs", label: "Recs" },
  { id: "eval", label: "Eval" },
] as const;
type PanelTab = (typeof PANEL_TABS)[number]["id"];

export default function App() {
  const [demoMode, setDemoMode] = useState(false);
  const [sideTab, setSideTab] = useState<SidebarTab>("overview");
  const [panelTab, setPanelTab] = useState<PanelTab>("cascade");
  const [activeSimulation, setActiveSimulation] = useState<SimulationResult | null>(null);
  const [simLoading, setSimLoading] = useState(false);

  // Fetch city graph (used by map)
  const { data: graphData, isLoading: graphLoading } = useCityGraph();

  const handleToggleDemo = useCallback(() => setDemoMode(p => !p), []);

  const handleSimulationComplete = useCallback((result: SimulationResult) => {
    setActiveSimulation(result);
    setSimLoading(false);
    // Auto-switch to cascade panel to show results
    setPanelTab("cascade");
  }, []);

  return (
    <div className={styles.app}>
      <TopBar
        demoMode={demoMode}
        onToggleDemo={handleToggleDemo}
        simulationId={activeSimulation?.simulation_id ?? null}
      />

      <div className={styles.body}>
        {/* ── Left Sidebar ── */}
        <aside className={styles.sidebar} aria-label="Control panel">
          <nav className={styles.sidenav} aria-label="Sidebar navigation">
            {SIDEBAR_TABS.map(tab => (
              <button
                key={tab.id}
                id={`sidebar-tab-${tab.id}`}
                className={`${styles.sidenav__tab} ${sideTab === tab.id ? styles["sidenav__tab--active"] : ""}`}
                onClick={() => setSideTab(tab.id)}
                aria-current={sideTab === tab.id ? "page" : undefined}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className={styles.sidenav__content}>
            {demoMode && <DemoBanner />}

            {sideTab === "overview" && (
              <OverviewPanel simulation={activeSimulation} simulationLoading={simLoading} />
            )}
            {sideTab === "weather" && (
              <WeatherPanel
                seed={42}
                demoData={demoMode ? DEMO_WEATHER_STATUS : null}
              />
            )}
            {sideTab === "simulate" && (
              <SimulationControls
                demoMode={demoMode}
                onSimulationComplete={handleSimulationComplete}
              />
            )}
          </div>
        </aside>

        {/* ── Map ── */}
        <main className={styles.map} aria-label="City map">
          <CityMap graphData={graphData ?? null} isLoading={graphLoading} />
        </main>

        {/* ── Right Panel ── */}
        <aside className={styles.panel} aria-label="Results panel">
          <nav className={styles.panelnav} aria-label="Results navigation">
            {PANEL_TABS.map(tab => (
              <button
                key={tab.id}
                id={`panel-tab-${tab.id}`}
                className={`${styles.panelnav__tab} ${panelTab === tab.id ? styles["panelnav__tab--active"] : ""}`}
                onClick={() => setPanelTab(tab.id)}
                aria-current={panelTab === tab.id ? "page" : undefined}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className={styles.panelnav__content}>
            {panelTab === "cascade" && (
              <CascadeTimelinePanel simulationId={activeSimulation?.simulation_id ?? null} />
            )}
            {panelTab === "recs" && (
              <RecommendationsPanel simulationId={activeSimulation?.simulation_id ?? null} />
            )}
            {panelTab === "eval" && (
              <EvaluationPanel demoMode={demoMode} />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
