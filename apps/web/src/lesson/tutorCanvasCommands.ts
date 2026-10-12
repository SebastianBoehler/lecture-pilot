import { applyCanvasSection } from "./agentTurnUi";
import type { AgentTurnResult } from "../shared/api";
import type { CanvasDocument } from "../shared/types";

export type CanvasNavigation = {
  focusedSectionId: string;
  highlightedBlockId: string | null;
  highlightedText: string | null;
  /** Bumped whenever the canvas should scroll to the current focus again. */
  version: number;
};

export const emptyCanvasNavigation: CanvasNavigation = {
  focusedSectionId: "",
  highlightedBlockId: null,
  highlightedText: null,
  version: 0,
};

/** Applies learner-section writes from one tutor turn to the loaded canvas. */
export function applyTutorSections(
  document: CanvasDocument | null,
  commands: AgentTurnResult["canvas_commands"],
) {
  return commands.reduce((current, command) => {
    const section = command.section;
    if ((command.type === "append_section" || command.type === "update_section") && section) {
      return applyCanvasSection(current, section, command.placement);
    }
    return current;
  }, document);
}

/** Derives where the canvas should focus and highlight after one tutor turn. */
export function navigateForTutorCommands(
  current: CanvasNavigation,
  commands: AgentTurnResult["canvas_commands"],
): CanvasNavigation {
  let focusSectionId: string | null = null;
  let generatedSectionId: string | null = null;
  let highlightedBlockId: string | null = null;
  let highlightSectionId: string | null = null;
  let highlightedText: string | null = null;
  for (const command of commands) {
    if (
      (command.type === "append_section" || command.type === "update_section") &&
      command.section
    ) {
      generatedSectionId = command.section_id ?? command.section.id;
    }
    if (command.type === "focus_section" && command.section_id) {
      focusSectionId = command.section_id;
    }
    if (command.type === "highlight_span" && command.span_id) {
      highlightedBlockId = command.span_id;
      highlightSectionId = command.section_id ?? null;
      highlightedText = command.highlight_text ?? null;
    }
  }
  const targetId = focusSectionId ?? generatedSectionId;
  if (targetId && highlightSectionId && highlightSectionId !== targetId) {
    highlightedBlockId = null;
    highlightedText = null;
  }
  return {
    focusedSectionId: targetId ?? current.focusedSectionId,
    highlightedBlockId,
    highlightedText,
    version: targetId || highlightedBlockId ? current.version + 1 : current.version,
  };
}
