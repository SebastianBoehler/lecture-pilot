import { ChevronLeft, FileText, MessageSquare, TableOfContents } from "lucide-react";
import { useState } from "react";

import { LessonCanvas } from "./LessonCanvas";
import { NotesPanel, OutlinePanel } from "./LessonSidePanels";
import { TutorDrawer } from "./TutorDrawer";
import type { CanvasSectionId, ChatMessage, DocumentAnchorId, Lecture, LessonPanelMode } from "./types";

export function LessonWorkspace({
  lecture,
  focusedSectionId,
  messages,
  panelMode,
  onBack,
  onSendMessage,
  onTogglePanel,
}: {
  lecture: Lecture;
  focusedSectionId: CanvasSectionId;
  messages: ChatMessage[];
  panelMode: LessonPanelMode | null;
  onBack: () => void;
  onSendMessage: (message: string) => Promise<void>;
  onTogglePanel: (mode: LessonPanelMode) => void;
}) {
  const layoutClass = panelMode ? "lesson-layout panel-open" : "lesson-layout";
  const [activeAnchorId, setActiveAnchorId] = useState<DocumentAnchorId | null>(null);

  function jumpToAnchor(anchorId: DocumentAnchorId) {
    setActiveAnchorId(anchorId);
    const anchor = document.getElementById(anchorId);
    if (typeof anchor?.scrollIntoView === "function") {
      anchor.scrollIntoView({ behavior: "smooth", block: "center" });
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
        <LessonCanvas
          lecture={lecture}
          focusedSectionId={focusedSectionId}
          activeAnchorId={activeAnchorId}
        />
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
      </aside>

      {panelMode === "chat" ? (
        <TutorDrawer messages={messages} onSendMessage={onSendMessage} />
      ) : null}
      {panelMode === "outline" ? (
        <OutlinePanel activeAnchorId={activeAnchorId} onJumpAnchor={jumpToAnchor} />
      ) : null}
      {panelMode === "notes" ? <NotesPanel lecture={lecture} /> : null}
    </main>
  );
}
