import { useState, type CSSProperties } from "react";

import { useI18n } from "./i18n";
import { percent, splitBars } from "./performanceMetrics";
import type { AnalyticsGateMetric, AnalyticsQuizMetric, LectureAnalyticsSummary } from "./types";

export function PerformanceInsights({
  analytics,
  view,
}: {
  analytics: LectureAnalyticsSummary;
  view: "quizzes" | "gates";
}) {
  const [selectedQuizId, setSelectedQuizId] = useState<string | null>(null);
  const [selectedGateId, setSelectedGateId] = useState<string | null>(null);

  if (view === "quizzes") {
    const selected =
      analytics.quizzes.find((quiz) => quiz.component_id === selectedQuizId) ??
      analytics.quizzes[0];
    return selected ? (
      <QuizBrowser quizzes={analytics.quizzes} selected={selected} onSelect={setSelectedQuizId} />
    ) : (
      <InsightEmpty kind="quizzes" />
    );
  }

  const selected =
    analytics.gates.find((gate) => gate.gate_id === selectedGateId) ?? analytics.gates[0];
  return selected ? (
    <GateBrowser gates={analytics.gates} selected={selected} onSelect={setSelectedGateId} />
  ) : (
    <InsightEmpty kind="gates" />
  );
}

function QuizBrowser({
  onSelect,
  quizzes,
  selected,
}: {
  onSelect: (id: string) => void;
  quizzes: AnalyticsQuizMetric[];
  selected: AnalyticsQuizMetric;
}) {
  const { t } = useI18n();
  return (
    <div className="insight-browser">
      <nav aria-label={t("analytics.quizList")} className="insight-browser-list">
        {quizzes.map((quiz, index) => (
          <button
            aria-current={quiz.component_id === selected.component_id ? "true" : undefined}
            className={quiz.component_id === selected.component_id ? "is-active" : undefined}
            key={quiz.component_id}
            type="button"
            onClick={() => onSelect(quiz.component_id)}
          >
            <span className="insight-item-index">{String(index + 1).padStart(2, "0")}</span>
            <span>
              <strong>{quiz.question}</strong>
              <small>
                {t("analytics.correct", {
                  count: quiz.unique_learners,
                  rate: percent(quiz.correct_rate),
                })}
              </small>
            </span>
          </button>
        ))}
      </nav>
      <article className="insight-browser-detail">
        <header>
          <span>{selected.title}</span>
          <h3>{selected.question}</h3>
          <p>
            {t("analytics.correct", {
              count: selected.unique_learners,
              rate: percent(selected.correct_rate),
            })}
          </p>
        </header>
        <QuizInsight quiz={selected} />
      </article>
    </div>
  );
}

function GateBrowser({
  gates,
  onSelect,
  selected,
}: {
  gates: AnalyticsGateMetric[];
  onSelect: (id: string) => void;
  selected: AnalyticsGateMetric;
}) {
  const { t } = useI18n();
  return (
    <div className="insight-browser">
      <nav aria-label={t("analytics.gateList")} className="insight-browser-list">
        {gates.map((gate, index) => (
          <button
            aria-current={gate.gate_id === selected.gate_id ? "true" : undefined}
            className={gate.gate_id === selected.gate_id ? "is-active" : undefined}
            key={gate.gate_id}
            type="button"
            onClick={() => onSelect(gate.gate_id)}
          >
            <span className="insight-item-index">{String(index + 1).padStart(2, "0")}</span>
            <span>
              <strong>{gate.gate_id}</strong>
              <small>
                {t("analytics.checksLearners", {
                  checks: gate.total_events,
                  learners: gate.unique_learners,
                })}
              </small>
            </span>
          </button>
        ))}
      </nav>
      <article className="insight-browser-detail">
        <header>
          <span>{t("analytics.gateEvidence")}</span>
          <h3>{selected.gate_id}</h3>
          <p>
            {t("analytics.checksLearners", {
              checks: selected.total_events,
              learners: selected.unique_learners,
            })}
          </p>
        </header>
        <GateInsight gate={selected} />
      </article>
    </div>
  );
}

function InsightEmpty({ kind }: { kind: "quizzes" | "gates" }) {
  const { t } = useI18n();
  return (
    <div className="performance-insight-empty">
      <strong>
        {t(kind === "quizzes" ? "analytics.noQuizEvidence" : "analytics.noGateEvidence")}
      </strong>
      <p>
        {t(kind === "quizzes" ? "analytics.noQuizEvidenceHelp" : "analytics.noGateEvidenceHelp")}
      </p>
    </div>
  );
}

function QuizInsight({ quiz }: { quiz: AnalyticsQuizMetric }) {
  const { t } = useI18n();
  return (
    <div className="analytics-insight-grid">
      <section>
        <h4>{t("analytics.answerDistribution")}</h4>
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
        <h4>{t("analytics.attendanceSplit")}</h4>
        <MetricBars values={splitBars(quiz.attendance_split)} />
      </section>
    </div>
  );
}

function GateInsight({ gate }: { gate: AnalyticsGateMetric }) {
  const { t } = useI18n();
  const assessedAttempts = gate.independent_attempts + gate.supported_attempts;
  return (
    <div className="analytics-insight-grid is-gate">
      <InsightSection title={t("analytics.gateOutcomes")} values={splitBars(gate.status_counts)} />
      <InsightSection
        title={t("analytics.independentLearning")}
        values={[
          {
            label: t("analytics.independentAttempts"),
            value: gate.independent_attempts,
            total: assessedAttempts,
          },
          {
            label: t("analytics.independentPasses"),
            value: gate.independent_passes,
            total: gate.independent_attempts,
            tone: "correct",
          },
          {
            label: t("analytics.supportedAttempts"),
            value: gate.supported_attempts,
            total: assessedAttempts,
          },
          {
            label: t("analytics.independentTransferPasses"),
            value: gate.independent_transfer_passes,
            total: gate.transfer_attempts,
            tone: "correct",
          },
        ]}
      />
      <InsightSection
        title={t("analytics.scaffoldsUsed")}
        values={splitBars(gate.assistance_level_counts)}
      />
      {Object.keys(gate.evidence_counts).length ? (
        <InsightSection
          title={t("analytics.demonstratedEvidence")}
          values={splitBars(gate.evidence_counts)}
        />
      ) : null}
      <InsightSection
        title={t("analytics.attendanceSplit")}
        values={splitBars(gate.attendance_split)}
      />
    </div>
  );
}

type MetricValue = {
  label: string;
  value: number;
  total: number;
  tone?: "correct" | "neutral" | "wrong";
};

function InsightSection({ title, values }: { title: string; values: MetricValue[] }) {
  return (
    <section>
      <h4>{title}</h4>
      <MetricBars values={values} />
    </section>
  );
}

function MetricBars({ values }: { values: MetricValue[] }) {
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
