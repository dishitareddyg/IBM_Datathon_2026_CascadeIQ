import { type FC } from "react";
import { useHealth } from "@/hooks/useApi";
import { formatDateTime } from "@/utils/formatting";
import styles from "./TopBar.module.css";

interface TopBarProps {
  demoMode: boolean;
  onToggleDemo: () => void;
  simulationId: string | null;
}

const TopBar: FC<TopBarProps> = ({ demoMode, onToggleDemo, simulationId }) => {
  const { data: health, isError: healthError } = useHealth();

  const graphStatus = healthError
    ? "unavailable"
    : health?.graph_loaded
      ? "live"
      : "stale";

  const now = new Date().toISOString();

  return (
    <header className={styles.topbar} role="banner">
      {/* Brand */}
      <div className={styles.topbar__brand}>
        <div className={styles.topbar__logo} aria-hidden="true">CQ</div>
        <div>
          <div className={styles.topbar__title}>CascadeIQ</div>
          <div className={styles.topbar__subtitle}>
            Bengaluru Urban · Emergency Response Simulator
          </div>
        </div>
      </div>

      <div className={styles.topbar__divider} aria-hidden="true" />

      {/* Status badges */}
      <div className={styles.topbar__status}>
        {/* Backend health */}
        {graphStatus === "live" && (
          <span className={`${styles.topbar__badge} ${styles["topbar__badge--live"]}`}>
            <span className={styles.topbar__dot} aria-hidden="true" />
            Graph loaded
          </span>
        )}
        {graphStatus === "unavailable" && (
          <span className={`${styles.topbar__badge} ${styles["topbar__badge--unavailable"]}`}>
            <span className={`${styles.topbar__dot} ${styles["topbar__dot--static"]}`} aria-hidden="true" />
            Backend unavailable
          </span>
        )}

        {/* Demo mode indicator */}
        {demoMode && (
          <span className={`${styles.topbar__badge} ${styles["topbar__badge--demo"]}`}>
            <span className={`${styles.topbar__dot} ${styles["topbar__dot--static"]}`} aria-hidden="true" />
            DEMO — fixture data
          </span>
        )}

        {/* Active simulation */}
        {simulationId && (
          <span className={`${styles.topbar__badge} ${styles["topbar__badge--simulated"]}`}>
            <span className={`${styles.topbar__dot} ${styles["topbar__dot--static"]}`} aria-hidden="true" />
            Simulation active
          </span>
        )}
      </div>

      <div className={styles.topbar__spacer} />

      {/* Actions */}
      <div className={styles.topbar__actions}>
        <span className={styles.topbar__timestamp} aria-label="Current time">
          {formatDateTime(now)}
        </span>
        <button
          id="demo-mode-toggle"
          className={`${styles.topbar__demo_toggle} ${demoMode ? styles["topbar__demo-toggle--active"] : ""}`}
          onClick={onToggleDemo}
          aria-pressed={demoMode}
          title={demoMode ? "Switch to API mode" : "Switch to demo mode (offline fixtures)"}
        >
          {demoMode ? "Exit Demo" : "Demo Mode"}
        </button>
      </div>
    </header>
  );
};

export default TopBar;
