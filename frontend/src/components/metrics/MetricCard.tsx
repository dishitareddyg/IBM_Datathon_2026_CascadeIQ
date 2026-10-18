import { type FC, type ReactNode } from "react";
import styles from "./MetricCard.module.css";

// ── KPI Card ───────────────────────────────────────────────────────────────────

interface KpiCardProps {
  id: string;
  label: string;
  value: string | number;
  sub?: string;
  variant?: "normal" | "warning" | "alert";
}

export const KpiCard: FC<KpiCardProps> = ({
  id,
  label,
  value,
  sub,
  variant = "normal",
}) => (
  <div
    id={id}
    className={`${styles["kpi-card"]} ${variant === "alert" ? styles["kpi-card--alert"] : ""} ${variant === "warning" ? styles["kpi-card--warning"] : ""}`}
  >
    <div className={styles["kpi-card__label"]}>{label}</div>
    <div
      className={`${styles["kpi-card__value"]} ${variant === "alert" ? styles["kpi-card__value--alert"] : ""} ${variant === "warning" ? styles["kpi-card__value--warning"] : ""}`}
      aria-label={`${label}: ${value}`}
    >
      {value}
    </div>
    {sub && <div className={styles["kpi-card__sub"]}>{sub}</div>}
  </div>
);

// ── KPI Grid ───────────────────────────────────────────────────────────────────

interface KpiGridProps {
  children: ReactNode;
}

export const KpiGrid: FC<KpiGridProps> = ({ children }) => (
  <div className={styles["kpi-grid"]}>{children}</div>
);

// ── Section Card ───────────────────────────────────────────────────────────────

interface SectionCardProps {
  title: string;
  badge?: ReactNode;
  children: ReactNode;
}

export const SectionCard: FC<SectionCardProps> = ({
  title,
  badge,
  children,
}) => (
  <div className={styles["section-card"]}>
    <div className={styles["section-card__header"]}>
      <span className={styles["section-card__title"]}>{title}</span>
      {badge && (
        <span className={styles["section-card__badge"]}>{badge}</span>
      )}
    </div>
    <div className={styles["section-card__body"]}>{children}</div>
  </div>
);

// ── Status Row ─────────────────────────────────────────────────────────────────

interface StatusRowProps {
  label: string;
  value: ReactNode;
}

export const StatusRow: FC<StatusRowProps> = ({ label, value }) => (
  <div className={styles["status-row"]}>
    <span className={styles["status-row__label"]}>{label}</span>
    <span className={styles["status-row__value"]}>{value}</span>
  </div>
);

// ── Source Badge ───────────────────────────────────────────────────────────────

type SourceVariant = "simulated" | "synthetic" | "live" | "historical";

interface SourceBadgeProps {
  source: SourceVariant | string;
}

export const SourceBadge: FC<SourceBadgeProps> = ({ source }) => {
  const lower = source.toLowerCase() as SourceVariant;
  return (
    <span
      className={`${styles["source-badge"]} ${styles[`source-badge--${lower}`] ?? ""}`}
    >
      {source}
    </span>
  );
};
