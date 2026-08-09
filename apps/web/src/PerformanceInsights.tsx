import { useState, type CSSProperties } from "react";

import { useI18n } from "./i18n";
import { percent } from "./performanceMetrics";
import type {
  AnalyticsGateMetric,
  AnalyticsOutcomeCell,
  AnalyticsQuizMetric,
  AnalyticsVersionStatus,
  LectureAnalyticsSummary,
} from "./types";

export function PerformanceInsights({
  analytics,
  view,
}: {
  analytics: LectureAnalyticsSummary;
  view: "quizzes" | "gates";
}) {
  const [selectedQuizKey, setSelectedQuizKey] = useState<string | null>(null);
  const [selectedGateKey, setSelectedGateKey] = useState<string | null>(null);
  if (view === "quizzes") {
    const selected =
      analytics.quizzes.find((quiz) => quizKey(quiz) === selectedQuizKey) ?? analytics.quizzes[0];
    return selected ? (
      <QuizBrowser quizzes={analytics.quizzes} selected={selected} onSelect={setSelectedQuizKey} />
    ) : (
      <InsightEmpty kind="quizzes" />
    );
  }
  const selected =
    analytics.gates.find((gate) => gateKey(gate) === selectedGateKey) ?? analytics.gates[0];
  return selected ? (
    <GateBrowser gates={analytics.gates} selected={selected} onSelect={setSelectedGateKey} />
  ) : (
    <InsightEmpty kind="gates" />
  );
}

function QuizBrowser({
  onSelect,
  quizzes,
  selected,
}: {
  onSelect: (key: string) => void;
  quizzes: AnalyticsQuizMetric[];
  selected: AnalyticsQuizMetric;
}) {
  const { t } = useI18n();
  return (
    <div className="insight-browser">
      <nav aria-label={t("analytics.quizList")} className="insight-browser-list">
        {quizzes.map((quiz, index) => (
          <button
            aria-current={quizKey(quiz) === quizKey(selected) ? "true" : undefined}
            className={quizKey(quiz) === quizKey(selected) ? "is-active" : undefined}
            key={quizKey(quiz)}
            type="button"
            onClick={() => onSelect(quizKey(quiz))}
          >
            <span className="insight-item-index">{String(index + 1).padStart(2, "0")}</span>
            <span>
              <strong>{quiz.question}</strong>
              <small>{outcomeSummary(quiz.first_attempt, t)}</small>
            </span>
          </button>
        ))}
      </nav>
      <article className="insight-browser-detail">
        <header>
          <span>{selected.title}</span>
          <h3>{selected.question}</h3>
          <VersionLabel version={selected.publication_version} status={selected.version_status} />
          <p>{t("analytics.activityEvents", { count: selected.activity_events })}</p>
        </header>
        <div className="analytics-insight-grid">
          <OutcomeSection cell={selected.first_attempt} title={t("analytics.quizFirstAttempt")} />
          <OutcomeSection
            cell={selected.correction_after_feedback}
            title={t("analytics.correctionAfterFeedback")}
          />
          {selected.options ? <OptionDistribution quiz={selected} /> : null}
        </div>
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
  onSelect: (key: string) => void;
  selected: AnalyticsGateMetric;
}) {
  const { t } = useI18n();
  return (
    <div className="insight-browser">
      <nav aria-label={t("analytics.gateList")} className="insight-browser-list">
        {gates.map((gate, index) => (
          <button
            aria-current={gateKey(gate) === gateKey(selected) ? "true" : undefined}
            className={gateKey(gate) === gateKey(selected) ? "is-active" : undefined}
            key={gateKey(gate)}
            type="button"
            onClick={() => onSelect(gateKey(gate))}
          >
            <span className="insight-item-index">{String(index + 1).padStart(2, "0")}</span>
            <span>
              <strong>{gate.gate_id}</strong>
              <small>{t("analytics.activityEvents", { count: gate.activity_events })}</small>
            </span>
          </button>
        ))}
      </nav>
      <article className="insight-browser-detail">
        <header>
          <span>{t("analytics.gateEvidence")}</span>
          <h3>{selected.gate_id}</h3>
          <VersionLabel version={selected.publication_version} status={selected.version_status} />
          {selected.gate_revision ? (
            <p>{t("analytics.gateRevision", { revision: selected.gate_revision })}</p>
          ) : null}
          <p>{t("analytics.activityEvents", { count: selected.activity_events })}</p>
        </header>
        <div className="analytics-insight-grid is-gate">
          <OutcomeSection
            cell={selected.independent_first_pass}
            title={t("analytics.independentFirstPass")}
          />
          <OutcomeSection cell={selected.supported_retry} title={t("analytics.supportedRetry")} />
          <OutcomeSection cell={selected.delayed_transfer} title={t("analytics.delayedTransfer")} />
        </div>
      </article>
    </div>
  );
}

function OutcomeSection({ cell, title }: { cell: AnalyticsOutcomeCell; title: string }) {
  const { t } = useI18n();
  return (
    <section className={`outcome-cell is-${cell.data_status}`}>
      <h4>{title}</h4>
      <strong>{cell.rate === null ? t("analytics.insufficientData") : percent(cell.rate)}</strong>
      <p>{outcomeSummary(cell, t)}</p>
    </section>
  );
}

function OptionDistribution({ quiz }: { quiz: AnalyticsQuizMetric }) {
  const { t } = useI18n();
  return (
    <section>
      <h4>{t("analytics.answerDistribution")}</h4>
      <div className="metric-bar-list">
        {quiz.options?.map((option) => (
          <div
            className={`metric-row is-${option.correct ? "correct" : "neutral"}`}
            key={option.option_index}
          >
            <div>
              <span>{`${String.fromCharCode(65 + option.option_index)} ${option.text}`}</span>
              <strong>{option.selections}</strong>
            </div>
            <div className="metric-track">
              <div
                className="metric-fill"
                style={barStyle(option.selections, quiz.first_attempt.sample_size)}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function VersionLabel({ status, version }: { status: AnalyticsVersionStatus; version: number }) {
  const { t } = useI18n();
  return (
    <p>
      {t("analytics.publicationVersion", {
        status: versionStatusLabel(status, t),
        version,
      })}
    </p>
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

function outcomeSummary(cell: AnalyticsOutcomeCell, t: ReturnType<typeof useI18n>["t"]) {
  return cell.data_status === "available"
    ? t("analytics.availableSample", { count: cell.sample_size })
    : t("analytics.insufficientSample", { count: cell.sample_size });
}

function versionStatusLabel(status: AnalyticsVersionStatus, t: ReturnType<typeof useI18n>["t"]) {
  if (status === "current") return t("analytics.version.current");
  return t("analytics.version.historical");
}

function quizKey(quiz: AnalyticsQuizMetric) {
  return `${quiz.component_id}:${quiz.publication_version}`;
}

function gateKey(gate: AnalyticsGateMetric) {
  return `${gate.gate_id}:${gate.gate_revision}:${gate.publication_version}`;
}

function barStyle(value: number, total: number): CSSProperties {
  return { "--metric-width": `${total ? Math.round((value / total) * 100) : 0}%` } as CSSProperties;
}
