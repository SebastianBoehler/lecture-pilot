import { CheckpointDrafts } from "./CheckpointDrafts";
import { FocusedCheckpoint, LearningEvidenceFlow } from "./LearningEvidenceFlow";
import { useCheckpointSupport } from "./useCheckpointSupport";
import { useTeachingLanguage } from "./useTeachingLanguage";
import { LessonControlRail } from "./LessonControlRail";
import { useEffect, useState } from "react";

import { useI18n } from "./i18n";
import { canvasWithPendingCheck } from "./canvasPendingCheck";
import { LessonCanvas } from "./LessonCanvas";
import { ProfessorLearnerPreviewBanner } from "./ProfessorLearnerPreviewBanner";
import { reconcileCanvasLearnerState, type PublishedCanvasView } from "./publishedCanvasView";
import { OutlinePanel } from "./LessonSidePanels";
import { scrollToCanvasAnchor } from "./canvasNavigation";
import type { LearnerQuizAnswerResult } from "./analyticsApi";
import type { TutorMessageOptions } from "./canvasLearningActions";
import type { LearnerLessonState } from "./learnerLessonStateTypes";
import { TutorDrawer } from "./TutorDrawer";
import { WorkspaceFilesPanel } from "./WorkspaceFilesPanel";
import { WorkspaceResetControl, type WorkspaceResetSelection } from "./WorkspaceResetControl";
import { useCanvasLearningAttempts } from "./useCanvasLearningAttempts";
import type {
  CanvasDocument,
  ChatMessage,
  DocumentAnchorId,
  Lecture,
  LessonPanelMode,
  LearnerWorkspaceMode,
  LoginSession,
  WorkspaceResource,
} from "./types";

export function LessonWorkspace({
  lecture,
  courseId,
  session,
  canvasDocument,
  publishedCanvasView,
  canvasError,
  focusedSectionId,
  highlightedBlockId,
  highlightedText,
  messages,
  navigationVersion,
  panelMode,
  learnerState,
  learnerStateError,
  tutorModel,
  previewMode = false,
  workspaceMode = "learner",
  onSendMessage,
  onPracticeSubmitted,
  onTogglePanel,
  onResetWorkspace,
}: {
  lecture: Lecture;
  courseId: string;
  session: LoginSession;
  canvasDocument: CanvasDocument | null;
  publishedCanvasView: PublishedCanvasView | null;
  canvasError: string | null;
  focusedSectionId: string;
  highlightedBlockId: string | null;
  highlightedText: string | null;
  messages: ChatMessage[];
  navigationVersion: number;
  panelMode: LessonPanelMode | null;
  learnerState: LearnerLessonState | null;
  learnerStateError: string | null;
  tutorModel: string | null;
  previewMode?: boolean;
  workspaceMode?: LearnerWorkspaceMode;
  onSendMessage: (message: string, options?: TutorMessageOptions) => Promise<void>;
  onPracticeSubmitted: (result: LearnerQuizAnswerResult) => void | Promise<void>;
  onTogglePanel: (mode: LessonPanelMode) => void;
  onResetWorkspace: (options: WorkspaceResetSelection) => Promise<void>;
}) {
  const { t } = useI18n();
  const language = useTeachingLanguage(
    courseId,
    lecture.id,
    session,
    canvasDocument,
    publishedCanvasView?.publication_version ?? null,
  );
  const support = useCheckpointSupport(courseId, lecture.id, session, workspaceMode, learnerState);
  const waitingForState = Boolean(
    publishedCanvasView &&
    canvasDocument &&
    (!support.state ||
      learnerStateError ||
      support.state.course_id !== courseId ||
      support.state.lecture_id !== lecture.id ||
      (publishedCanvasView &&
        support.state.publication_version !== publishedCanvasView.publication_version)),
  );
  const focused = waitingForState || support.state?.pending_check?.focus_required === true;
  const layoutClass = panelMode && !focused ? "lesson-layout panel-open" : "lesson-layout";
  const [activeAnchorId, setActiveAnchorId] = useState<DocumentAnchorId | null>(null);
  const [outlinePulse, setOutlinePulse] = useState<{
    id: DocumentAnchorId;
    version: number;
  } | null>(null);
  const [selectedResource, setSelectedResource] = useState<WorkspaceResource | null>(null);
  const learningAttempts = useCanvasLearningAttempts({
    courseId,
    lecture,
    session,
    workspaceMode,
    openChat: () => panelMode !== "chat" && onTogglePanel("chat"),
    onPracticeSubmitted,
    onSendMessage,
  });
  const canvasLearnerState = reconcileCanvasLearnerState(publishedCanvasView, support.state);

  useEffect(() => {
    if (!outlinePulse) {
      return undefined;
    }
    const timeout = window.setTimeout(() => setOutlinePulse(null), 5000);
    return () => window.clearTimeout(timeout);
  }, [outlinePulse]);

  function jumpToAnchor(anchorId: DocumentAnchorId) {
    setActiveAnchorId(anchorId);
    setOutlinePulse((current) => ({ id: anchorId, version: (current?.version ?? 0) + 1 }));
    scrollToCanvasAnchor(anchorId);
  }

  function openWorkspaceResource(resource: WorkspaceResource) {
    selectWorkspaceResource(resource);
    if (panelMode !== "files") {
      onTogglePanel("files");
    }
  }

  function selectWorkspaceResource(resource: WorkspaceResource) {
    setSelectedResource(resource);
    if (!resource.sectionId) return;
    const targetId = resource.blockId ?? resource.sectionId;
    setActiveAnchorId(targetId);
    setOutlinePulse((current) => ({ id: targetId, version: (current?.version ?? 0) + 1 }));
    scrollToCanvasAnchor(targetId);
  }

  return (
    <CheckpointDrafts
      key={`${session.tenant_id}:${session.username}:${workspaceMode}:${courseId}:${lecture.id}:${publishedCanvasView?.publication_version}`}
    >
      <main className={layoutClass}>
        <section className="lesson-main">
          {previewMode ? <ProfessorLearnerPreviewBanner /> : null}
          <div className="lesson-toolbar">
            <div className="lesson-toolbar-actions">
              {!focused ? language.control : null}
              <WorkspaceResetControl disabled={!canvasDocument} onReset={onResetWorkspace} />
            </div>
            <span>{lecture.date}</span>
          </div>
          {canvasError ? <p className="form-error">{canvasError}</p> : null}
          {learnerStateError ? (
            <p className="form-error" role="alert">
              {learnerStateError}
            </p>
          ) : null}
          {canvasLearnerState.requiresReconciliation ? (
            <div className="form-error" role="alert">
              <p>{t("quiz.publicationChanged")}</p>
              <button type="button" onClick={() => window.location.reload()}>
                {t("quiz.reloadLecture")}
              </button>
            </div>
          ) : null}
          {learningAttempts.coachingError ? (
            <p className="form-error" role="alert">
              {learningAttempts.coachingError}
            </p>
          ) : null}
          {!canvasDocument && !canvasError ? (
            <p className="drawer-note">{t("lesson.loadingCanvas")}</p>
          ) : null}
          {canvasDocument ? (
            <LearningEvidenceFlow state={canvasLearnerState.currentLearnerState} />
          ) : null}
          {waitingForState ? (
            <p role="status">Checking the saved attempt before opening teaching…</p>
          ) : canvasDocument && focused && canvasLearnerState.currentLearnerState ? (
            <FocusedCheckpoint
              state={canvasLearnerState.currentLearnerState}
              document={canvasDocument}
              onSubmit={learningAttempts.submitCheckpoint}
              onHelp={support.requestHelp}
              busy={support.busy}
              error={support.error}
            />
          ) : canvasDocument ? (
            <LessonCanvas
              canvasDocument={canvasWithPendingCheck(
                language.document ?? canvasDocument,
                canvasLearnerState.currentLearnerState?.pending_check,
              )}
              focusedSectionId={focusedSectionId}
              highlightedBlockId={highlightedBlockId}
              highlightedText={highlightedText}
              activeAnchorId={activeAnchorId}
              navigationVersion={navigationVersion}
              outlinePulseId={outlinePulse?.id ?? null}
              outlinePulseVersion={outlinePulse?.version ?? 0}
              session={session}
              quizStates={canvasLearnerState.quizStates}
              publicationVersion={canvasLearnerState.publicationVersion}
              onOpenResource={openWorkspaceResource}
              onSubmitCheckpoint={learningAttempts.submitCheckpoint}
              onSubmitQuizAnswer={learningAttempts.submitQuiz}
            />
          ) : null}
        </section>

        {!focused ? (
          <LessonControlRail panelMode={panelMode} onTogglePanel={onTogglePanel} />
        ) : null}

        {!focused && panelMode === "chat" ? (
          <TutorDrawer
            messages={messages}
            model={tutorModel}
            sessionGoal={canvasLearnerState.currentLearnerState?.active_session_goal ?? null}
            onClose={() => onTogglePanel("chat")}
            onSendMessage={onSendMessage}
          />
        ) : null}
        {!focused && panelMode === "outline" ? (
          <OutlinePanel
            activeAnchorId={activeAnchorId ?? focusedSectionId}
            learnerState={canvasLearnerState.currentLearnerState}
            canvasDocument={canvasDocument}
            onClose={() => onTogglePanel("outline")}
            onJumpAnchor={jumpToAnchor}
          />
        ) : null}
        {!focused && panelMode === "files" ? (
          <WorkspaceFilesPanel
            canvasDocument={canvasDocument}
            session={session}
            selectedResource={selectedResource}
            onClose={() => onTogglePanel("files")}
            onSelectResource={selectWorkspaceResource}
          />
        ) : null}
      </main>
    </CheckpointDrafts>
  );
}
