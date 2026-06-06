import { ChevronLeft, FileText, FolderTree, MessageSquare, TableOfContents } from "lucide-react";
import { useEffect, useState } from "react";

import { LessonCanvas } from "./LessonCanvas";
import { NotesPanel, OutlinePanel } from "./LessonSidePanels";
import { TutorDrawer } from "./TutorDrawer";
import { WorkspaceFilesPanel } from "./WorkspaceFilesPanel";
import type {
  CanvasDocument,
  ChatMessage,
  DocumentAnchorId,
  Lecture,
  LessonPanelMode,
  WorkspaceResource,
} from "./types";

export function LessonWorkspace({
  lecture,
  canvasDocument,
  canvasError,
  focusedSectionId,
  highlightedBlockId,
  highlightedText,
  messages,
  navigationVersion,
  panelMode,
  onBack,
  onSendMessage,
  onTogglePanel,
}: {
  lecture: Lecture;
  canvasDocument: CanvasDocument | null;
  canvasError: string | null;
  focusedSectionId: string;
  highlightedBlockId: string | null;
  highlightedText: string | null;
  messages: ChatMessage[];
  navigationVersion: number;
  panelMode: LessonPanelMode | null;
  onBack: () => void;
  onSendMessage: (message: string) => Promise<void>;
  onTogglePanel: (mode: LessonPanelMode) => void;
}) {
  const layoutClass = panelMode ? "lesson-layout panel-open" : "lesson-layout";
  const [activeAnchorId, setActiveAnchorId] = useState<DocumentAnchorId | null>(null);
  const [outlinePulse, setOutlinePulse] = useState<{ id: DocumentAnchorId; version: number } | null>(
    null,
  );
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
    setSelectedResource(resource);
    if (panelMode !== "files") {
      onTogglePanel("files");
    }
  }

  return (
    <main className={layoutClass}>
      <section className="lesson-main">
        <div className="lesson-toolbar">
          <button className="ghost-button" type="button" onClick={onBack}>
            <ChevronLeft size={17} />
            Dashboard
          </button>
          <span>{lecture.date}</span>
        </div>
        {canvasError ? <p className="form-error">{canvasError}</p> : null}
        {!canvasDocument && !canvasError ? <p className="drawer-note">Loading lecture canvas...</p> : null}
        {canvasDocument ? (
          <LessonCanvas
            canvasDocument={canvasDocument}
            lecture={lecture}
            focusedSectionId={focusedSectionId}
            highlightedBlockId={highlightedBlockId}
            highlightedText={highlightedText}
            activeAnchorId={activeAnchorId}
            navigationVersion={navigationVersion}
            outlinePulseId={outlinePulse?.id ?? null}
            outlinePulseVersion={outlinePulse?.version ?? 0}
            onOpenResource={openWorkspaceResource}
          />
        ) : null}
      </section>

      <aside className="rail" aria-label="Lesson controls">
        <button
          className={panelMode === "chat" ? "rail-button is-active" : "rail-button"}
          type="button"
          aria-label={panelMode === "chat" ? "Close tutor chat" : "Open tutor chat"}
          aria-pressed={panelMode === "chat"}
          onClick={() => onTogglePanel("chat")}
        >
          <MessageSquare size={18} />
        </button>
        <button
          className={panelMode === "outline" ? "rail-button is-active" : "rail-button"}
          type="button"
          aria-label="Open document outline"
          aria-pressed={panelMode === "outline"}
          onClick={() => onTogglePanel("outline")}
        >
          <TableOfContents size={18} />
        </button>
        <button
          className={panelMode === "notes" ? "rail-button is-active" : "rail-button"}
          type="button"
          aria-label="Open lecture notes panel"
          aria-pressed={panelMode === "notes"}
          onClick={() => onTogglePanel("notes")}
        >
          <FileText size={18} />
        </button>
        <button
          className={panelMode === "files" ? "rail-button is-active" : "rail-button"}
          type="button"
          aria-label="Open file workspace"
          aria-pressed={panelMode === "files"}
          onClick={() => onTogglePanel("files")}
        >
          <FolderTree size={18} />
        </button>
      </aside>

      {panelMode === "chat" ? (
        <TutorDrawer messages={messages} onSendMessage={onSendMessage} />
      ) : null}
      {panelMode === "outline" ? (
        <OutlinePanel
          activeAnchorId={activeAnchorId}
          canvasDocument={canvasDocument}
          onJumpAnchor={jumpToAnchor}
        />
      ) : null}
      {panelMode === "notes" ? <NotesPanel lecture={lecture} /> : null}
      {panelMode === "files" ? (
        <WorkspaceFilesPanel
          canvasDocument={canvasDocument}
          lecture={lecture}
          selectedResource={selectedResource}
          onSelectResource={setSelectedResource}
        />
      ) : null}
    </main>
  );
}
