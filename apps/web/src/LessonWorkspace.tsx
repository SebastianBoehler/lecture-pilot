import { FileText, FolderTree, GitBranch, MessageSquare, TableOfContents } from "lucide-react";
import { useEffect, useState } from "react";

import { useI18n } from "./i18n";
import { LessonCanvas } from "./LessonCanvas";
import { LearningPathPanel } from "./LearningPathPanel";
import { ProfessorLearnerPreviewBanner } from "./ProfessorLearnerPreviewBanner";
import { NotesPanel, OutlinePanel } from "./LessonSidePanels";
import { recordQuizAnswer } from "./analyticsApi";
import { TutorDrawer } from "./TutorDrawer";
import { WorkspaceFilesPanel } from "./WorkspaceFilesPanel";
import { WorkspaceResetControl, type WorkspaceResetSelection } from "./WorkspaceResetControl";
import type {
  CanvasDocument,
  CanvasBlock,
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
  canvasError,
  focusedSectionId,
  highlightedBlockId,
  highlightedText,
  messages,
  navigationVersion,
  panelMode,
  passedGateIds,
  tutorModel,
  previewMode = false,
  workspaceMode = "learner",
  onSendMessage,
  onTogglePanel,
  onResetWorkspace,
}: {
  lecture: Lecture;
  courseId: string;
  session: LoginSession;
  canvasDocument: CanvasDocument | null;
  canvasError: string | null;
  focusedSectionId: string;
  highlightedBlockId: string | null;
  highlightedText: string | null;
  messages: ChatMessage[];
  navigationVersion: number;
  panelMode: LessonPanelMode | null;
  passedGateIds: string[];
  tutorModel: string | null;
  previewMode?: boolean;
  workspaceMode?: LearnerWorkspaceMode;
  onSendMessage: (message: string) => Promise<void>;
  onTogglePanel: (mode: LessonPanelMode) => void;
  onResetWorkspace: (options: WorkspaceResetSelection) => Promise<void>;
}) {
  const { t } = useI18n();
  const layoutClass = panelMode ? "lesson-layout panel-open" : "lesson-layout";
  const [activeAnchorId, setActiveAnchorId] = useState<DocumentAnchorId | null>(null);
  const [outlinePulse, setOutlinePulse] = useState<{
    id: DocumentAnchorId;
    version: number;
  } | null>(null);
  const [selectedResource, setSelectedResource] = useState<WorkspaceResource | null>(null);

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
    const anchor = document.getElementById(anchorId);
    if (typeof anchor?.scrollIntoView === "function") {
      anchor.scrollIntoView({ behavior: "smooth", block: "center" });
    }
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
    const target = document.getElementById(targetId);
    if (typeof target?.scrollIntoView === "function") {
      target.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  function submitQuizAnswer(block: CanvasBlock, answer: string, optionIndex: number) {
    if (panelMode !== "chat") {
      onTogglePanel("chat");
    }
    void recordQuizAnswer({
      courseId,
      lectureId: lecture.id,
      attendance: lecture.attendance,
      blockId: block.id,
      optionIndex,
      session,
      mode: workspaceMode,
    }).catch(() => undefined);
    void onSendMessage(quizAnswerMessage(block, answer, optionIndex));
  }

  return (
    <main className={layoutClass}>
      <section className="lesson-main">
        {previewMode ? <ProfessorLearnerPreviewBanner /> : null}
        <div className="lesson-toolbar">
          <div className="lesson-toolbar-actions">
            <WorkspaceResetControl disabled={!canvasDocument} onReset={onResetWorkspace} />
          </div>
          <span>{lecture.date}</span>
        </div>
        {canvasError ? <p className="form-error">{canvasError}</p> : null}
        {!canvasDocument && !canvasError ? (
          <p className="drawer-note">{t("lesson.loadingCanvas")}</p>
        ) : null}
        {canvasDocument ? (
          <LessonCanvas
            canvasDocument={canvasDocument}
            focusedSectionId={focusedSectionId}
            highlightedBlockId={highlightedBlockId}
            highlightedText={highlightedText}
            activeAnchorId={activeAnchorId}
            navigationVersion={navigationVersion}
            outlinePulseId={outlinePulse?.id ?? null}
            outlinePulseVersion={outlinePulse?.version ?? 0}
            session={session}
            onOpenResource={openWorkspaceResource}
            onSubmitQuizAnswer={submitQuizAnswer}
          />
        ) : null}
      </section>

      <aside className="rail" aria-label={t("lesson.controls")}>
        <button
          id="lesson-panel-trigger-chat"
          className={panelMode === "chat" ? "rail-button is-active" : "rail-button"}
          type="button"
          aria-label={panelMode === "chat" ? t("lesson.closeChat") : t("lesson.openChat")}
          aria-controls="lesson-panel"
          aria-expanded={panelMode === "chat"}
          aria-pressed={panelMode === "chat"}
          onClick={() => onTogglePanel("chat")}
        >
          <MessageSquare size={18} />
        </button>
        <button
          id="lesson-panel-trigger-outline"
          className={panelMode === "outline" ? "rail-button is-active" : "rail-button"}
          type="button"
          aria-label={panelMode === "outline" ? t("lesson.closeOutline") : t("lesson.openOutline")}
          aria-controls="lesson-panel"
          aria-expanded={panelMode === "outline"}
          aria-pressed={panelMode === "outline"}
          onClick={() => onTogglePanel("outline")}
        >
          <TableOfContents size={18} />
        </button>
        <button
          id="lesson-panel-trigger-path"
          className={panelMode === "path" ? "rail-button is-active" : "rail-button"}
          type="button"
          aria-label={panelMode === "path" ? t("lesson.closePath") : t("lesson.openPath")}
          aria-controls="lesson-panel"
          aria-expanded={panelMode === "path"}
          aria-pressed={panelMode === "path"}
          onClick={() => onTogglePanel("path")}
        >
          <GitBranch size={18} />
        </button>
        <button
          id="lesson-panel-trigger-notes"
          className={panelMode === "notes" ? "rail-button is-active" : "rail-button"}
          type="button"
          aria-label={panelMode === "notes" ? t("lesson.closeNotes") : t("lesson.openNotes")}
          aria-controls="lesson-panel"
          aria-expanded={panelMode === "notes"}
          aria-pressed={panelMode === "notes"}
          onClick={() => onTogglePanel("notes")}
        >
          <FileText size={18} />
        </button>
        <button
          id="lesson-panel-trigger-files"
          className={panelMode === "files" ? "rail-button is-active" : "rail-button"}
          type="button"
          aria-label={panelMode === "files" ? t("lesson.closeFiles") : t("lesson.openFiles")}
          aria-controls="lesson-panel"
          aria-expanded={panelMode === "files"}
          aria-pressed={panelMode === "files"}
          onClick={() => onTogglePanel("files")}
        >
          <FolderTree size={18} />
        </button>
      </aside>

      {panelMode === "chat" ? (
        <TutorDrawer
          messages={messages}
          model={tutorModel}
          onClose={() => onTogglePanel("chat")}
          onSendMessage={onSendMessage}
        />
      ) : null}
      {panelMode === "outline" ? (
        <OutlinePanel
          activeAnchorId={activeAnchorId}
          canvasDocument={canvasDocument}
          onClose={() => onTogglePanel("outline")}
          onJumpAnchor={jumpToAnchor}
        />
      ) : null}
      {panelMode === "path" ? (
        <LearningPathPanel
          activeAnchorId={activeAnchorId}
          courseId={courseId}
          focusedSectionId={focusedSectionId}
          lecture={lecture}
          passedGateIds={passedGateIds}
          session={session}
          onClose={() => onTogglePanel("path")}
          onJumpAnchor={jumpToAnchor}
        />
      ) : null}
      {panelMode === "notes" ? (
        <NotesPanel lecture={lecture} onClose={() => onTogglePanel("notes")} />
      ) : null}
      {panelMode === "files" ? (
        <WorkspaceFilesPanel
          canvasDocument={canvasDocument}
          session={session}
          selectedResource={selectedResource}
          onClose={() => onTogglePanel("files")}
          onSelectResource={selectWorkspaceResource}
        />
      ) : null}
    </main>
  );
}

function quizAnswerMessage(block: CanvasBlock, answer: string, optionIndex: number) {
  const letter = String.fromCharCode(65 + optionIndex);
  const prompt = block.text?.trim();
  const title = block.caption?.trim() || "retrieval quiz";
  return [
    `Retrieval quiz answer for "${title}": ${letter}. ${answer}`,
    prompt ? `Question: ${prompt}` : "",
  ]
    .filter(Boolean)
    .join("\n");
}
