import { FileText, FolderTree, GitBranch, MessageSquare, TableOfContents } from "lucide-react";
import { useI18n } from "./i18n";
import type { LessonPanelMode } from "./types";

const controls = [
  ["chat", MessageSquare, "lesson.openChat", "lesson.closeChat"],
  ["outline", TableOfContents, "lesson.openOutline", "lesson.closeOutline"],
  ["path", GitBranch, "lesson.openPath", "lesson.closePath"],
  ["notes", FileText, "lesson.openNotes", "lesson.closeNotes"],
  ["files", FolderTree, "lesson.openFiles", "lesson.closeFiles"],
] as const;

export function LessonControlRail({
  panelMode,
  onTogglePanel,
}: {
  panelMode: LessonPanelMode | null;
  onTogglePanel: (mode: LessonPanelMode) => void;
}) {
  const { t } = useI18n();
  return (
    <aside className="rail" aria-label={t("lesson.controls")}>
      {controls.map(([mode, Icon, open, close]) => (
        <button
          key={mode}
          id={`lesson-panel-trigger-${mode}`}
          className={panelMode === mode ? "rail-button is-active" : "rail-button"}
          type="button"
          aria-label={t(panelMode === mode ? close : open)}
          aria-controls="lesson-panel"
          aria-expanded={panelMode === mode}
          aria-pressed={panelMode === mode}
          onClick={() => onTogglePanel(mode)}
        >
          <Icon size={18} />
        </button>
      ))}
    </aside>
  );
}
