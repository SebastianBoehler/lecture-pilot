import type { CSSProperties } from "react";

import { useI18n } from "./i18n";
import { percent } from "./performanceMetrics";
import type { AnalyticsGateMetric, LectureAnalyticsSummary } from "./types";

export function ProfessorLearningMapTree({ analytics }: { analytics: LectureAnalyticsSummary }) {
  const { t } = useI18n();
  const learningMap = analytics.learning_map;
  if (!learningMap?.nodes.length) return null;

  const gatesById = new Map(learningMap.gates.map((gate) => [gate.id, gate]));
  const metricsById = new Map(analytics.gates.map((gate) => [gate.gate_id, gate]));

  return (
    <section className="learning-map-panel" aria-labelledby="learning-path-gates-title">
      <header className="learning-map-panel-header">
        <div>
          <p>{learningMap.title}</p>
          <h3 id="learning-path-gates-title">{t("analytics.learningPathGates")}</h3>
        </div>
        <span>{t("analytics.concepts", { count: learningMap.nodes.length })}</span>
      </header>

      <ol className="learning-map-tree">
        {learningMap.nodes.map((node, index) => (
          <li className="learning-map-node" key={node.id}>
            <span className="learning-map-index">{String(index + 1).padStart(2, "0")}</span>
            <div className="learning-map-node-body">
              <header>
                <div>
                  <strong>{node.title}</strong>
                  {node.source_ref ? <small>{node.source_ref}</small> : null}
                </div>
                {node.quiz_ids.length ? (
                  <span>{t("analytics.quizCount", { count: node.quiz_ids.length })}</span>
                ) : null}
              </header>

              {node.prerequisites.length ? (
                <p className="learning-map-prerequisites">
                  {t("analytics.unlocksAfter", {
                    prerequisites: node.prerequisites.join(", "),
                  })}
                </p>
              ) : null}

              <div className="learning-map-gates">
                {node.gate_ids.length ? (
                  node.gate_ids.map((gateId) => (
                    <GateRate
                      gateId={gateId}
                      key={gateId}
                      metric={metricsById.get(gateId)}
                      title={gatesById.get(gateId)?.title ?? gateId}
                      t={t}
                    />
                  ))
                ) : (
                  <span className="learning-map-empty-gate">{t("analytics.noGateAttached")}</span>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function GateRate({
  gateId,
  metric,
  t,
  title,
}: {
  gateId: string;
  metric?: AnalyticsGateMetric;
  t: (
    key:
      | "analytics.passed"
      | "analytics.noAttempts"
      | "analytics.checkCount"
      | "analytics.zeroChecks"
      | "analytics.learners",
    params?: Record<string, string | number>,
  ) => string;
  title: string;
}) {
  const total = metric?.total_events ?? 0;
  const passed = metric?.status_counts.passed ?? 0;
  const passRate = total ? passed / total : null;
  return (
    <article className="learning-map-gate">
      <div className="learning-map-gate-header">
        <strong>{title}</strong>
        <span>
          {total ? t("analytics.passed", { rate: percent(passRate) }) : t("analytics.noAttempts")}
        </span>
      </div>
      <div className="learning-map-gate-meta">
        <span>{gateId}</span>
        <span>
          {total ? t("analytics.checkCount", { passed, total }) : t("analytics.zeroChecks")}
        </span>
        {metric?.unique_learners ? (
          <span>{t("analytics.learners", { count: metric.unique_learners })}</span>
        ) : null}
      </div>
      <div className="learning-map-gate-track" aria-hidden="true">
        <div className="learning-map-gate-fill" style={gateFillStyle(passRate)} />
      </div>
    </article>
  );
}

function gateFillStyle(value: number | null): CSSProperties {
  return {
    "--learning-map-gate-rate": `${value === null ? 0 : Math.round(value * 100)}%`,
  } as CSSProperties;
}
