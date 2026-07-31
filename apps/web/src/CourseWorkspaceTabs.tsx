import type { KeyboardEvent } from "react";

import { useI18n } from "./i18n";

export type CourseWorkspaceTool = "lectures" | "readiness" | "practice";

const TOOLS: CourseWorkspaceTool[] = ["lectures", "readiness", "practice"];

export function CourseWorkspaceTabs({
  activeTool,
  idBase,
  onChange,
}: {
  activeTool: CourseWorkspaceTool;
  idBase: string;
  onChange: (tool: CourseWorkspaceTool) => void;
}) {
  const { t } = useI18n();

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex: number | null = null;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % TOOLS.length;
    if (event.key === "ArrowLeft") nextIndex = (index - 1 + TOOLS.length) % TOOLS.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = TOOLS.length - 1;
    if (nextIndex === null) return;

    event.preventDefault();
    const nextTool = TOOLS[nextIndex];
    onChange(nextTool);
    document.getElementById(tabId(idBase, nextTool))?.focus();
  }

  return (
    <div aria-label={t("dashboard.studyTools")} className="workspace-tabs" role="tablist">
      {TOOLS.map((tool, index) => (
        <button
          aria-controls={panelId(idBase, tool)}
          aria-selected={activeTool === tool}
          className={activeTool === tool ? "is-active" : undefined}
          id={tabId(idBase, tool)}
          key={tool}
          role="tab"
          tabIndex={activeTool === tool ? 0 : -1}
          type="button"
          onClick={() => onChange(tool)}
          onKeyDown={(event) => handleKeyDown(event, index)}
        >
          {t(`dashboard.tab.${tool}`)}
        </button>
      ))}
    </div>
  );
}

export function panelId(idBase: string, tool: CourseWorkspaceTool) {
  return `${idBase}-${tool}-panel`;
}

export function tabId(idBase: string, tool: CourseWorkspaceTool) {
  return `${idBase}-${tool}-tab`;
}
