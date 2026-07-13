import { AlertTriangle, CheckCircle2, ChevronDown, Circle, GitBranch } from "lucide-react";
import { useId, useState, type CSSProperties } from "react";

import { useI18n } from "./i18n";
import type { MessageKey } from "./i18nMessages";
import { buildLearningTree, type LearningTreeBranch } from "./learningTree";
import { percent } from "./performanceMetrics";
import type { LearningMapGate, LearningMapNode } from "./learningMapTypes";
import type { AnalyticsGateMetric, LectureAnalyticsSummary } from "./types";

type Translator = (key: MessageKey, params?: Record<string, string | number>) => string;
type ConceptState = {
  kind: "healthy" | "watch" | "attention" | "empty";
  label: string;
};

export function ProfessorLearningMapTree({ analytics }: { analytics: LectureAnalyticsSummary }) {
  const { t } = useI18n();
  const learningMap = analytics.learning_map;
  if (!learningMap?.nodes.length) return null;

  const gatesById = new Map(learningMap.gates.map((gate) => [gate.id, gate]));
  const metricsById = new Map(analytics.gates.map((gate) => [gate.gate_id, gate]));
  const titlesById = new Map(learningMap.nodes.map((node) => [node.id, node.title]));
  const tree = buildLearningTree(learningMap.nodes);

  return (
    <section className="learning-map-panel" aria-labelledby="learning-path-gates-title">
      <header className="learning-map-panel-header">
        <div>
          <h3 id="learning-path-gates-title">{t("analytics.learningPathGates")}</h3>
        </div>
        <span className="learning-map-concept-count">
          <GitBranch aria-hidden="true" size={14} />
          {t("analytics.concepts", { count: learningMap.nodes.length })}
        </span>
      </header>

      <ol
        className="learning-map-tree"
        aria-label={`${learningMap.title} ${t("analytics.learningPathGates")}`}
      >
        {tree.map((branch) => (
          <ConceptBranch
            branch={branch}
            gatesById={gatesById}
            key={branch.node.id}
            metricsById={metricsById}
            t={t}
            titlesById={titlesById}
          />
        ))}
      </ol>
    </section>
  );
}

function ConceptBranch({
  branch,
  gatesById,
  metricsById,
  t,
  titlesById,
}: {
  branch: LearningTreeBranch<LearningMapNode>;
  gatesById: Map<string, LearningMapGate>;
  metricsById: Map<string, AnalyticsGateMetric>;
  t: Translator;
  titlesById: Map<string, string>;
}) {
  const [expanded, setExpanded] = useState(false);
  const detailsId = useId();
  const { node } = branch;
  const state = conceptState(node, metricsById, t);
  const prerequisiteTitles = node.prerequisites.map(
    (prerequisiteId) => titlesById.get(prerequisiteId) ?? prerequisiteId,
  );

  return (
    <li className={`learning-map-node is-${state.kind}`}>
      <button
        aria-controls={detailsId}
        aria-expanded={expanded}
        className="learning-map-node-toggle"
        type="button"
        onClick={() => setExpanded((value) => !value)}
      >
        <span className="learning-map-node-marker">
          <ConceptStateIcon kind={state.kind} />
        </span>
        <span className="learning-map-node-copy">
          <strong>{node.title}</strong>
          <small>{state.label}</small>
        </span>
        <span className="learning-map-node-meta">
          {node.quiz_ids.length ? (
            <span>{t("analytics.quizCount", { count: node.quiz_ids.length })}</span>
          ) : null}
          <ChevronDown aria-hidden="true" className={expanded ? "is-open" : ""} size={15} />
        </span>
      </button>

      {expanded ? (
        <div className="learning-map-node-details" id={detailsId}>
          {node.source_ref ? (
            <small className="learning-map-source">{node.source_ref}</small>
          ) : null}
          {prerequisiteTitles.length ? (
            <p className="learning-map-prerequisites">
              {t("analytics.unlocksAfter", {
                prerequisites: prerequisiteTitles.join(", "),
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
      ) : null}

      {branch.children.length ? (
        <ol
          className={`learning-map-branch ${branch.children.length === 1 ? "is-chain" : "is-fork"}`}
        >
          {branch.children.map((child) => (
            <ConceptBranch
              branch={child}
              gatesById={gatesById}
              key={child.node.id}
              metricsById={metricsById}
              t={t}
              titlesById={titlesById}
            />
          ))}
        </ol>
      ) : null}
    </li>
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
  t: Translator;
  title: string;
}) {
  const total = metric?.total_events ?? 0;
  const passed = metric?.status_counts.passed ?? 0;
  const passRate = total ? passed / total : null;
  const kind = total === 0 ? "empty" : passed === total ? "healthy" : "attention";
  const label = total
    ? t("analytics.passed", { rate: percent(passRate) })
    : t("analytics.noAttempts");

  return (
    <article className={`learning-map-gate is-${kind}`}>
      <div className="learning-map-gate-header">
        <strong>{title}</strong>
        <span>
          <ConceptStateIcon kind={kind} size={13} />
          {label}
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

function conceptState(
  node: LearningMapNode,
  metricsById: Map<string, AnalyticsGateMetric>,
  t: Translator,
): ConceptState {
  if (!node.gate_ids.length) {
    return { kind: "empty", label: t("analytics.noGateAttached") };
  }
  const metrics = node.gate_ids.map((id) => metricsById.get(id));
  const total = metrics.reduce((sum, metric) => sum + (metric?.total_events ?? 0), 0);
  const passed = metrics.reduce((sum, metric) => sum + (metric?.status_counts.passed ?? 0), 0);
  if (!total) return { kind: "empty", label: t("analytics.noAttempts") };
  const kind = passed === total ? "healthy" : passed ? "watch" : "attention";
  return { kind, label: t("analytics.passed", { rate: percent(passed / total) }) };
}

function ConceptStateIcon({ kind, size = 16 }: { kind: ConceptState["kind"]; size?: number }) {
  if (kind === "healthy") return <CheckCircle2 aria-hidden="true" size={size} />;
  if (kind === "watch" || kind === "attention") {
    return <AlertTriangle aria-hidden="true" size={size} />;
  }
  return <Circle aria-hidden="true" size={size} />;
}

function gateFillStyle(value: number | null): CSSProperties {
  return {
    "--learning-map-gate-rate": `${value === null ? 0 : Math.round(value * 100)}%`,
  } as CSSProperties;
}
