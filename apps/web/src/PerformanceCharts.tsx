import type { CSSProperties } from "react";

import { useI18n } from "./i18n";
import { analyticsSignals, percent } from "./performanceMetrics";
import type { LectureAnalyticsSummary } from "./types";

export function AnalyticsChart({ analytics }: { analytics: LectureAnalyticsSummary }) {
  const { t } = useI18n();
  const signals = analyticsSignals(analytics);
  return (
    <section className="performance-chart" aria-label={t("analytics.selectedOverview")}>
      <div className="performance-signal">
        <span>{t("analytics.quizSuccess")}</span>
        <strong>{percent(signals.quizRate)}</strong>
        <SignalBar tone="success" value={signals.quizRate} />
      </div>
      <div className="performance-signal">
        <span>{t("analytics.gatePassRate")}</span>
        <strong>{percent(signals.gateRate)}</strong>
        <SignalBar tone="warning" value={signals.gateRate} />
      </div>
      <div className="attendance-chart">
        <span>{t("analytics.attendanceSplit")}</span>
        <StackedBar values={signals.attendance} />
      </div>
    </section>
  );
}

function SignalBar({ value, tone }: { value: number | null; tone: "success" | "warning" }) {
  return (
    <span className={`signal-track is-${tone}`} aria-hidden="true">
      <span
        className="signal-fill"
        style={
          {
            "--signal-width": `${Math.round(Math.max(0, Math.min(1, value ?? 0)) * 100)}%`,
          } as CSSProperties
        }
      />
    </span>
  );
}

function StackedBar({ values }: { values: Record<string, number> }) {
  const { t } = useI18n();
  const total = Object.values(values).reduce((sum, value) => sum + value, 0);
  return (
    <div className="stacked-bar">
      {Object.entries(values).map(([label, value]) => (
        <span
          className={`is-${label}`}
          key={label}
          style={
            {
              "--segment-width": `${total ? Math.round((value / total) * 100) : 0}%`,
            } as CSSProperties
          }
        >
          {attendanceLabel(label, t)} {value}
        </span>
      ))}
    </div>
  );
}

function attendanceLabel(label: string, t: ReturnType<typeof useI18n>["t"]) {
  if (label === "present") return t("attendance.present");
  if (label === "absent") return t("attendance.absent");
  if (label === "unknown") return t("attendance.unknown");
  return label;
}
