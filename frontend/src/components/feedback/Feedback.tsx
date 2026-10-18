import { type FC, type ReactNode } from "react";
import styles from "./Feedback.module.css";
import { ApiError } from "@/services/apiClient";

// ── Loading Spinner ────────────────────────────────────────────────────────────

interface SpinnerProps {
  label?: string;
  fullHeight?: boolean;
}

export const LoadingSpinner: FC<SpinnerProps> = ({
  label = "Loading…",
  fullHeight = false,
}) => (
  <div
    className={`${styles.spinner} ${fullHeight ? styles["spinner--fullheight"] : ""}`}
    role="status"
    aria-label={label}
  >
    <div className={styles.spinner__ring} aria-hidden="true" />
    <span>{label}</span>
  </div>
);

// ── Error Banner ───────────────────────────────────────────────────────────────

interface ErrorBannerProps {
  error: unknown;
  title?: string;
}

export const ErrorBanner: FC<ErrorBannerProps> = ({ error, title }) => {
  const apiErr = error instanceof ApiError ? error : null;
  const displayTitle = title ?? (apiErr ? `Error: ${apiErr.code}` : "Error");
  const message =
    error instanceof Error
      ? error.message
      : "An unexpected error occurred.";

  return (
    <div className={styles["error-banner"]} role="alert">
      <span className={styles["error-banner__icon"]} aria-hidden="true">⚠</span>
      <div className={styles["error-banner__content"]}>
        <div className={styles["error-banner__title"]}>{displayTitle}</div>
        <div className={styles["error-banner__message"]}>{message}</div>
        {apiErr && (
          <div className={styles["error-banner__code"]}>
            Status {apiErr.status} · {apiErr.code}
          </div>
        )}
      </div>
    </div>
  );
};

// ── Empty State ────────────────────────────────────────────────────────────────

interface EmptyStateProps {
  icon?: string;
  title: string;
  message?: string;
}

export const EmptyState: FC<EmptyStateProps> = ({
  icon = "○",
  title,
  message,
}) => (
  <div className={styles["empty-state"]}>
    <div className={styles["empty-state__icon"]} aria-hidden="true">{icon}</div>
    <div className={styles["empty-state__title"]}>{title}</div>
    {message && (
      <div className={styles["empty-state__message"]}>{message}</div>
    )}
  </div>
);

// ── Disclaimer Banner ──────────────────────────────────────────────────────────

interface DisclaimerProps {
  text: string;
}

export const DisclaimerBanner: FC<DisclaimerProps> = ({ text }) => (
  <div className={styles.disclaimer} role="note">
    <span className={styles.disclaimer__icon} aria-hidden="true">⚠</span>
    <span className={styles.disclaimer__text}>{text}</span>
  </div>
);

// ── Demo Mode Banner ───────────────────────────────────────────────────────────

export const DemoBanner: FC = () => (
  <div className={styles["demo-banner"]} role="note">
    <span className={styles["demo-banner__icon"]} aria-hidden="true">🔬</span>
    <span className={styles["demo-banner__text"]}>
      <strong>Demo mode active.</strong> All data shown below is from bundled
      fixtures, not the live API. Switch off demo mode to use the backend.
    </span>
  </div>
);

// ── Stale Badge ────────────────────────────────────────────────────────────────

interface StaleBadgeProps {
  age: string;
}

export const StaleBadge: FC<StaleBadgeProps> = ({ age }) => (
  <span className={styles["stale-badge"]}>stale · {age}</span>
);
