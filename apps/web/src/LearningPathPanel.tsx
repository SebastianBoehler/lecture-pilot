import { CheckCircle2, Circle, LockKeyhole, PlayCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { getLectureLearningMap } from "./learningMapApi";
import { useI18n } from "./i18n";
import type { LearningMap, LearningMapGate, LearningMapNode } from "./learningMapTypes";
import type { DocumentAnchorId, Lecture, LoginSession } from "./types";

export function LearningPathPanel({
  activeAnchorId,
  courseId,
  focusedSectionId,
  lecture,
  passedGateIds,
  session,
  onJumpAnchor,
}: {
  activeAnchorId: DocumentAnchorId | null;
  courseId: string;
  focusedSectionId: string;
  lecture: Lecture;
  passedGateIds: string[];
  session: LoginSession;
  onJumpAnchor: (anchorId: DocumentAnchorId) => void;
}) {
  const { t } = useI18n();
  const [learningMap, setLearningMap] = useState<LearningMap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const passedGates = useMemo(() => new Set(passedGateIds), [passedGateIds]);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setLearningMap(null);
    getLectureLearningMap(courseId, lecture.id, session)
      .then((payload) => {
        if (!cancelled) setLearningMap(payload);
      })
      .catch((fetchError) => {
        if (!cancelled) {
          setError(fetchError instanceof Error ? fetchError.message : t("path.loading"));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [courseId, lecture.id, session, t]);

  const gatesById = useMemo(
    () => new Map((learningMap?.gates ?? []).map((gate) => [gate.id, gate])),
    [learningMap],
  );
  const currentIndex = Math.max(
    0,
    learningMap?.nodes.findIndex((node) => isActiveNode(node, activeAnchorId, focusedSectionId)) ??
      0,
  );

  return (
    <aside className="drawer" aria-label={t("path.panel")}>
      <div className="drawer-section">
        <h2>{t("path.title")}</h2>
        {error ? <p className="form-error">{error}</p> : null}
        {!learningMap && !error ? <p className="drawer-note">{t("path.loading")}</p> : null}
        {learningMap ? (
          <ol
            className="student-path-tree"
            aria-label={t("path.list", { title: learningMap.title })}
          >
            {learningMap.nodes.map((node, index) => (
              <PathNode
                active={isActiveNode(node, activeAnchorId, focusedSectionId)}
                gateLookup={gatesById}
                index={index}
                key={node.id}
                node={node}
                passedGateIds={passedGates}
                status={nodeStatus(index, currentIndex)}
                statusLabel={statusLabel(nodeStatus(index, currentIndex), t)}
                t={t}
                onJumpAnchor={onJumpAnchor}
              />
            ))}
          </ol>
        ) : null}
      </div>
    </aside>
  );
}

function PathNode({
  active,
  gateLookup,
  index,
  node,
  passedGateIds,
  status,
  statusLabel,
  t,
  onJumpAnchor,
}: {
  active: boolean;
  gateLookup: Map<string, LearningMapGate>;
  index: number;
  node: LearningMapNode;
  passedGateIds: Set<string>;
  status: "done" | "current" | "upcoming";
  statusLabel: string;
  t: (key: "path.check.passed" | "path.check.gate" | "path.check.quiz") => string;
  onJumpAnchor: (anchorId: DocumentAnchorId) => void;
}) {
  return (
    <li className={`student-path-node is-${status} ${active ? "is-active" : ""}`}>
      <button
        aria-label={node.title}
        aria-pressed={active}
        className="student-path-node-button"
        onClick={() => onJumpAnchor(node.section_id)}
        type="button"
      >
        <StatusIcon status={status} />
        <span>
          <span className="student-path-step">{String(index + 1).padStart(2, "0")}</span>
          <strong>{node.title}</strong>
          <small>{statusLabel}</small>
        </span>
      </button>
      {node.gate_ids.length || node.quiz_ids.length ? (
        <div className="student-path-checks">
          {node.gate_ids.map((gateId) => (
            <PathCheck
              key={gateId}
              label={gateLookup.get(gateId)?.title ?? gateId}
              passed={passedGateIds.has(gateId)}
              statusLabel={
                passedGateIds.has(gateId) ? t("path.check.passed") : t("path.check.gate")
              }
            />
          ))}
          {node.quiz_ids.map((quizId) => (
            <PathCheck
              key={quizId}
              label={quizId}
              passed={false}
              statusLabel={t("path.check.quiz")}
            />
          ))}
        </div>
      ) : null}
    </li>
  );
}

function PathCheck({
  label,
  passed,
  statusLabel,
}: {
  label: string;
  passed: boolean;
  statusLabel: string;
}) {
  return (
    <span className={passed ? "student-path-check is-passed" : "student-path-check"}>
      {passed ? <CheckCircle2 size={13} /> : <Circle size={13} />}
      {statusLabel}
      <strong>{label}</strong>
    </span>
  );
}

function StatusIcon({ status }: { status: "done" | "current" | "upcoming" }) {
  if (status === "done") return <CheckCircle2 size={17} />;
  if (status === "current") return <PlayCircle size={17} />;
  return <LockKeyhole size={17} />;
}

function isActiveNode(
  node: LearningMapNode,
  activeAnchorId: DocumentAnchorId | null,
  focusedSectionId: string,
) {
  return (
    node.section_id === activeAnchorId ||
    node.section_id === focusedSectionId ||
    node.gate_ids.includes(activeAnchorId ?? "") ||
    node.quiz_ids.includes(activeAnchorId ?? "")
  );
}

function nodeStatus(index: number, currentIndex: number) {
  if (index < currentIndex) return "done";
  if (index === currentIndex) return "current";
  return "upcoming";
}

function statusLabel(
  status: "done" | "current" | "upcoming",
  t: (key: "path.status.visited" | "path.status.current" | "path.status.upcoming") => string,
) {
  if (status === "done") return t("path.status.visited");
  if (status === "current") return t("path.status.current");
  return t("path.status.upcoming");
}
