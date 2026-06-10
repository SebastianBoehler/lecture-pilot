import { render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";

import { TutorDrawer } from "./TutorDrawer";

it("keeps the composer docked and renders only the latest tool tags outside messages", () => {
  render(
    <TutorDrawer
      messages={[
        {
          id: "agent-1",
          role: "agent",
          content: "Look at the risk section with \\lambda_{ik}.",
          toolTags: [
            "focus: old-section",
            "highlight: losses-and-risks-p-1",
            "phrase: loss function \\lambda_{ik}",
            "gate: needs evidence",
          ],
        },
      ]}
      model="openrouter/google/gemini-3.1-flash-lite"
      onSendMessage={vi.fn()}
    />,
  );

  const messageBubble = screen.getByText(/Look at the risk section/).closest(".chat-message");
  expect(messageBubble).not.toBeNull();
  expect(within(messageBubble as HTMLElement).queryByLabelText("Tool calls")).not.toBeInTheDocument();
  expect(document.body.textContent).not.toContain("\\lambda");

  const toolCalls = screen.getByLabelText("Tool calls");
  expect(toolCalls.closest(".chat-message")).toBeNull();
  expect(within(toolCalls).queryByText("focus: old-section")).not.toBeInTheDocument();
  expect(within(toolCalls).getByText("+1 earlier")).toBeInTheDocument();
  expect(within(toolCalls).getByText("highlight: losses-and-risks-p-1")).toBeInTheDocument();
  expect(within(toolCalls).getByText(/phrase: loss function/)).toBeInTheDocument();
  expect(within(toolCalls).getByText("gate: needs evidence")).toBeInTheDocument();

  const composer = screen.getByPlaceholderText("Ask about this lecture...");
  expect(composer.closest(".chat-dock")).not.toBeNull();
  expect(composer.closest(".message-list")).toBeNull();
});
