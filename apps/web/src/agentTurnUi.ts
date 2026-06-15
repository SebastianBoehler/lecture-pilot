import type { AgentTurnResult } from "./api";
import type { CanvasDocument, CanvasSection, ChatMessage } from "./types";

export function applyCanvasSection(document: CanvasDocument | null, section: CanvasSection) {
  if (!document) {
    return document;
  }
  const sectionIndex = document.sections.findIndex((candidate) => candidate.id === section.id);
  if (sectionIndex === -1) {
    return { ...document, sections: [...document.sections, section] };
  }
  const sections = [...document.sections];
  sections[sectionIndex] = section;
  return { ...document, sections };
}

export function pendingTutorMessage(id: string): ChatMessage {
  return {
    id,
    role: "agent",
    content: "Working through the lecture canvas...",
    isPending: true,
  };
}

export function appendLiveToolTag(messages: ChatMessage[], messageId: string, tag: string) {
  if (!isVisibleToolActivity(tag)) {
    return messages;
  }
  return messages.map((message) => {
    if (message.id !== messageId) return message;
    return {
      ...message,
      toolTags: [...(message.toolTags ?? []), tag],
    };
  });
}

export function completePendingTutorMessage(
  messages: ChatMessage[],
  messageId: string,
  result: AgentTurnResult,
): ChatMessage[] {
  return messages.map((message) => {
    if (message.id !== messageId) return message;
    return {
      id: messageId,
      role: "agent" as const,
      content: result.message,
      toolTags: toolTagsFromResult(result),
    };
  });
}

export function toolTagsFromResult(result: AgentTurnResult): string[] {
  const commandTags = result.canvas_commands.flatMap((command) => {
    if (command.type === "focus_section" && command.section_id) {
      return [`focus: ${command.section_id}`];
    }
    if (command.type === "open_artifact" && command.artifact_id) {
      return [`artifact: ${command.artifact_id}`];
    }
    if (command.type === "highlight_span" && command.span_id) {
      return command.highlight_text
        ? [`highlight: ${command.span_id}`, `phrase: ${command.highlight_text}`]
        : [`highlight: ${command.span_id}`];
    }
    if ((command.type === "append_section" || command.type === "update_section") && command.section_id) {
      return [`canvas: ${command.section_id}`];
    }
    return [];
  });
  const gateTags = result.quality_gate
    ? [`gate: ${result.quality_gate.status.replace("_", " ")}`]
    : [];
  return [...commandTags, ...gateTags];
}

const hiddenActivityTags = new Set([
  "call tutor model",
  "load learner memory",
  "prepare canvas update",
  "read canvas",
  "save attendance",
  "save quality gate",
  "write canvas update",
]);

function isVisibleToolActivity(tag: string) {
  return !hiddenActivityTags.has(tag);
}
