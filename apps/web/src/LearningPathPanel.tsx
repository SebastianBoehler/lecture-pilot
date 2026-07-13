import { CheckCircle2, Circle, PlayCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useI18n } from "./i18n";
import type { MessageKey } from "./i18nMessages";
import { LessonDrawerClose } from "./LessonDrawerClose";
import { getLectureLearningMap } from "./learningMapApi";
import { buildLearningTree, type LearningTreeBranch } from "./learningTree";
import type { LearningMap, LearningMapGate, LearningMapNode } from "./learningMapTypes";
import type { DocumentAnchorId, Lecture, LoginSession } from "./types";

type PathStatus = "current" | "available";
type Translator = (key: MessageKey, params?: Record<string, string | number>) => string;

export function LearningPathPanel({
  activeAnchorId,
  courseId,
  focusedSectionId,
  lecture,
  passedGateIds,
  session,
  onClose,
  onJumpAnchor,
}: {
  activeAnchorId: DocumentAnchorId | null;
  courseId: string;
  focusedSectionId: string;
  lecture: Lecture;
  passedGateIds: string[];
  session: LoginSession;
  onClose: () => void;
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
  const tree = useMemo(() => buildLearningTree(learningMap?.nodes ?? []), [learningMap]);
  const indexById = useMemo(
    () => new Map((learningMap?.nodes ?? []).map((node, index) => [node.id, index])),
    [learningMap],
  );
  const titlesById = useMemo(
    () => new Map((learningMap?.nodes ?? []).map((node) => [node.id, node.title])),
    [learningMap],
  );

  return (
    <aside className="drawer learning-path-drawer" id="lesson-panel" aria-label={t("path.panel")}>
      <LessonDrawerClose returnFocusId="lesson-panel-trigger-path" onClose={onClose} />
      <div className="drawer-section learning-path-section">
        <header className="learning-path-heading">
          <h2>{t("path.title")}</h2>
          {learningMap ? <p>{learningMap.title}</p> : null}
        </header>
        {error ? <p className="form-error">{error}</p> : null}
        {!learningMap && !error ? <p className="drawer-note">{t("path.loading")}</p> : null}
        {learningMap ? (
          <ol
            className="student-path-tree"
            aria-label={t("path.list", { title: learningMap.title })}
          >
            {tree.map((branch) => (
              <PathBranch
                activeAnchorId={activeAnchorId}
                branch={branch}
                focusedSectionId={focusedSectionId}
                gateLookup={gatesById}
                indexById={indexById}
                key={branch.node.id}
                passedGateIds={passedGates}
                t={t}
                titlesById={titlesById}
                onJumpAnchor={onJumpAnchor}
              />
            ))}
          </ol>
        ) : null}
      </div>
    </aside>
  );
}

function PathBranch({
  activeAnchorId,
  branch,
  focusedSectionId,
  gateLookup,
  indexById,
  passedGateIds,
  t,
  titlesById,
  onJumpAnchor,
}: {
  activeAnchorId: DocumentAnchorId | null;
  branch: LearningTreeBranch<LearningMapNode>;
  focusedSectionId: string;
  gateLookup: Map<string, LearningMapGate>;
  indexById: Map<string, number>;
  passedGateIds: Set<string>;
  t: Translator;
  titlesById: Map<string, string>;
  onJumpAnchor: (anchorId: DocumentAnchorId) => void;
}) {
  const { node } = branch;
  const index = indexById.get(node.id) ?? 0;
  const active = isActiveNode(node, activeAnchorId, focusedSectionId);
  const status: PathStatus = active ? "current" : "available";
  const label = statusLabel(status, t);
  const prerequisiteTitles = node.prerequisites.map(
    (prerequisiteId) => titlesById.get(prerequisiteId) ?? prerequisiteId,
  );

  return (
    <li className={`student-path-node is-${status} ${active ? "is-active" : ""}`}>
      <button
        aria-current={active ? "step" : undefined}
        aria-label={`${node.title}, ${label}`}
        aria-pressed={active}
        className="student-path-node-button"
        type="button"
        onClick={() => onJumpAnchor(node.section_id)}
      >
        <span className="student-path-marker">
          <StatusIcon status={status} />
        </span>
        <span className="student-path-node-copy">
          <span className="student-path-node-meta">
            <span className="student-path-step">{String(index + 1).padStart(2, "0")}</span>
            <small>{label}</small>
          </span>
          <strong>{node.title}</strong>
          {prerequisiteTitles.length ? (
            <span className="student-path-prerequisites">
              {t("path.unlocksAfter", { prerequisites: prerequisiteTitles.join(", ") })}
            </span>
          ) : null}
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

      {branch.children.length ? (
        <ol
          className={`student-path-branch ${branch.children.length === 1 ? "is-chain" : "is-fork"}`}
        >
          {branch.children.map((child) => (
            <PathBranch
              activeAnchorId={activeAnchorId}
              branch={child}
              focusedSectionId={focusedSectionId}
              gateLookup={gateLookup}
              indexById={indexById}
              key={child.node.id}
              passedGateIds={passedGateIds}
              t={t}
              titlesById={titlesById}
              onJumpAnchor={onJumpAnchor}
            />
          ))}
        </ol>
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
      {passed ? (
        <CheckCircle2 aria-hidden="true" size={13} />
      ) : (
        <Circle aria-hidden="true" size={13} />
      )}
      <span>{statusLabel}</span>
      <strong>{label}</strong>
    </span>
  );
}

function StatusIcon({ status }: { status: PathStatus }) {
  if (status === "current") return <PlayCircle aria-hidden="true" size={16} />;
  return <Circle aria-hidden="true" size={15} />;
}

function isActiveNode(
  node: LearningMapNode,
  activeAnchorId: DocumentAnchorId | null,
  focusedSectionId: string,
) {
  if (!activeAnchorId) return node.section_id === focusedSectionId;
  return (
    node.section_id === activeAnchorId ||
    node.gate_ids.includes(activeAnchorId) ||
    node.quiz_ids.includes(activeAnchorId)
  );
}

function statusLabel(status: PathStatus, t: Translator) {
  if (status === "current") return t("path.status.current");
  return t("path.status.available");
}
