import type { CSSProperties } from "react";

import { AnalyticsEmptyState } from "./AnalyticsEmptyState";
import { useI18n } from "./i18n";
import { percent, splitBars } from "./performanceMetrics";
import type { AnalyticsGateMetric, AnalyticsQuizMetric, LectureAnalyticsSummary } from "./types";

export function PerformanceInsights({ analytics }: { analytics: LectureAnalyticsSummary }) {
  const { t } = useI18n();
  if (!analytics.total_events) return <AnalyticsEmptyState />;
  return (
    <div className="analytics-summary">
      <section className="analytics-column" aria-label={t("analytics.quizInsights")}>
        <h3>{t("analytics.quizFriction")}</h3>
        {analytics.quizzes.map((quiz) => (
          <article className="analytics-panel" key={quiz.component_id}>
            <header>
              <strong>{quiz.title}</strong>
              <small>
                {t("analytics.correct", {
                  count: quiz.unique_learners,
                  rate: percent(quiz.correct_rate),
                })}
              </small>
            </header>
            <p>{quiz.question}</p>
            <QuizInsight quiz={quiz} />
          </article>
        ))}
      </section>
      <section className="analytics-column" aria-label={t("analytics.gateInsights")}>
        <h3>{t("analytics.gateEvidence")}</h3>
        {analytics.gates.map((gate) => (
          <article className="analytics-panel" key={gate.gate_id}>
            <header>
              <strong>{gate.gate_id}</strong>
              <small>
                {t("analytics.checksLearners", {
                  checks: gate.total_events,
                  learners: gate.unique_learners,
                })}
              </small>
            </header>
            <GateInsight gate={gate} />
          </article>
        ))}
      </section>
    </div>
  );
}

function QuizInsight({ quiz }: { quiz: AnalyticsQuizMetric }) {
  const { t } = useI18n();
  return (
    <div className="analytics-insight-grid">
      <section>
        <h3>{t("analytics.answerDistribution")}</h3>
        <MetricBars
          values={quiz.options.map((option) => ({
            label: `${String.fromCharCode(65 + option.option_index)} ${option.text}`,
            value: option.selections,
            total: quiz.total_attempts,
            tone: option.correct ? "correct" : "wrong",
          }))}
        />
      </section>
      <section>
        <h3>{t("analytics.attendanceSplit")}</h3>
        <MetricBars values={splitBars(quiz.attendance_split)} />
      </section>
    </div>
  );
}

function GateInsight({ gate }: { gate: AnalyticsGateMetric }) {
  const { t } = useI18n();
  return (
    <div className="analytics-insight-grid">
      <section>
        <h3>{t("analytics.gateOutcomes")}</h3>
        <MetricBars values={splitBars(gate.status_counts)} />
      </section>
      <section>
        <h3>{t("analytics.attendanceSplit")}</h3>
        <MetricBars values={splitBars(gate.attendance_split)} />
      </section>
    </div>
  );
}

function MetricBars({
  values,
}: {
  values: Array<{
    label: string;
    value: number;
    total: number;
    tone?: "correct" | "neutral" | "wrong";
  }>;
}) {
  return (
    <div className="metric-bar-list">
      {values.map((item) => (
        <div className={`metric-row is-${item.tone ?? "neutral"}`} key={item.label}>
          <div>
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
          <div className="metric-track">
            <div className="metric-fill" style={barStyle(item.value, item.total)} />
          </div>
        </div>
      ))}
    </div>
  );
}

function barStyle(value: number, total: number): CSSProperties {
  return { "--metric-width": `${total ? Math.round((value / total) * 100) : 0}%` } as CSSProperties;
}
