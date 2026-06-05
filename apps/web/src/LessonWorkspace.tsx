import { ChevronLeft, FileText, Grid2X2, MessageSquare } from "lucide-react";

import { LessonCanvas } from "./LessonCanvas";
import { ArtifactsPanel, NotesPanel } from "./LessonSidePanels";
import { TutorDrawer } from "./TutorDrawer";
import type { CanvasSectionId, ChatMessage, Lecture, LessonPanelMode } from "./types";

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
        <LessonCanvas lecture={lecture} focusedSectionId={focusedSectionId} />
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
          className={panelMode === "artifacts" ? "rail-button is-active" : "rail-button"}
          type="button"
          aria-label="Open artifacts panel"
          aria-pressed={panelMode === "artifacts"}
          onClick={() => onTogglePanel("artifacts")}
        >
          <Grid2X2 size={18} />
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
      {panelMode === "artifacts" ? <ArtifactsPanel /> : null}
      {panelMode === "notes" ? <NotesPanel lecture={lecture} /> : null}
    </main>
  );
}
