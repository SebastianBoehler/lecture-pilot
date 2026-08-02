import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { renderWithI18n } from "./test/renderWithI18n";
import { TutorDrawer } from "./TutorDrawer";

it("renders assistant tool tags between the triggering user turn and assistant answer", () => {
  renderWithI18n(
    <TutorDrawer
      messages={[
        {
          id: "user-1",
          role: "user",
          content: "Can you explain the risk section?",
        },
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
      onClose={vi.fn()}
      onSendMessage={vi.fn()}
    />,
  );

  const userBubble = screen.getByText(/Can you explain the risk section/).closest(".chat-message");
  const agentBubble = screen.getByText(/Look at the risk section/).closest(".chat-message");
  expect(userBubble).not.toBeNull();
  expect(agentBubble).not.toBeNull();
  expect(within(agentBubble as HTMLElement).queryByLabelText("Tool calls")).not.toBeInTheDocument();
  expect((agentBubble as HTMLElement).querySelector(".katex")).not.toBeNull();

  const toolCalls = screen.getByLabelText("Tool calls");
  expect(toolCalls.closest(".chat-message")).toBeNull();
  expect(
    (userBubble as HTMLElement).compareDocumentPosition(toolCalls) &
      Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
  expect(
    toolCalls.compareDocumentPosition(agentBubble as HTMLElement) &
      Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
  const history = within(toolCalls).getByText("+1 earlier").closest("details");
  expect(history).not.toBeNull();
  expect(history).not.toHaveAttribute("open");
  expect(within(history as HTMLElement).getByText("focus: old-section")).toBeInTheDocument();
  expect(within(toolCalls).getByText("highlight: losses-and-risks-p-1")).toBeInTheDocument();
  expect(
    within(toolCalls)
      .getByText(/phrase: loss function/)
      .closest(".tool-tag"),
  ).toHaveClass("tool-tag-detail");
  expect(within(toolCalls).getByText("gate: needs evidence")).toBeInTheDocument();

  const composer = screen.getByPlaceholderText("Ask about this lecture...");
  expect(composer.closest(".chat-dock")).not.toBeNull();
  expect(composer.closest(".message-list")).toBeNull();
});

it("shows live activity tags while a tutor turn is pending", () => {
  renderWithI18n(
    <TutorDrawer
      messages={[
        {
          id: "agent-pending",
          role: "agent",
          content: "Working through the lecture canvas...",
          isPending: true,
          toolTags: ["read request", "call tutor model"],
        },
      ]}
      model={null}
      onClose={vi.fn()}
      onSendMessage={vi.fn()}
    />,
  );

  expect(screen.getByText("Working...")).toBeInTheDocument();
  const pendingBubble = screen
    .getByText(/Working through the lecture canvas/)
    .closest(".chat-message");
  const toolCalls = screen.getByLabelText("Tool calls");
  expect(pendingBubble).not.toBeNull();
  expect(pendingBubble as HTMLElement).toHaveAttribute("aria-busy", "true");
  expect(
    toolCalls.compareDocumentPosition(pendingBubble as HTMLElement) &
      Node.DOCUMENT_POSITION_FOLLOWING,
  ).toBeTruthy();
  expect(screen.getByText("read request")).toBeInTheDocument();
  expect(screen.getByText("call tutor model")).toBeInTheDocument();
});

it("restores a failed tutor message in the composer for retry", async () => {
  const user = userEvent.setup();
  let rejectTurn: (reason: Error) => void = () => undefined;
  const onSendMessage = vi.fn(
    () =>
      new Promise<void>((_resolve, reject) => {
        rejectTurn = reject;
      }),
  );
  renderWithI18n(
    <TutorDrawer messages={[]} model={null} onClose={vi.fn()} onSendMessage={onSendMessage} />,
  );

  const composer = screen.getByRole("textbox", { name: "Tutor message" });
  await user.type(composer, "Why is this tokenization wrong?");
  await user.click(screen.getByRole("button", { name: "Send message" }));

  expect(composer).toBeDisabled();
  await act(async () => {
    rejectTurn(
      new Error("OpenAI API credits are exhausted. Add credits, then retry this tutor message."),
    );
  });
  expect(await screen.findByText(/OpenAI API credits are exhausted/i)).toBeInTheDocument();
  expect(composer).toHaveValue("Why is this tokenization wrong?");
  expect(composer).toBeEnabled();
});
