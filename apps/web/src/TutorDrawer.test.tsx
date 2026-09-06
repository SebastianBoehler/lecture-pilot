import { act, fireEvent, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { renderWithI18n } from "./test/renderWithI18n";
import { TutorDrawer } from "./TutorDrawer";
import { I18nProvider } from "./i18n";

it("keeps the activity timeline collapsed between the question and answer", async () => {
  renderWithI18n(
    <TutorDrawer
      messages={[
        { id: "user-1", role: "user", content: "Explain risk?" },
        {
          id: "agent-1",
          role: "agent",
          content: "Consider \\lambda_{ik}.",
          toolTags: [
            "read: canvas/index.md",
            "focus: risk",
            "phrase: loss function",
            "gate: needs evidence",
          ],
        },
      ]}
      model="openrouter/google/gemini-3.1-flash-lite"
      sessionGoal="Explain the decision under uncertainty."
      onClose={vi.fn()}
      onSendMessage={vi.fn()}
    />,
  );
  const activity = screen.getByLabelText("Tutor activity");
  const timeline = within(activity).getByText("4 actions").closest("details");
  expect(timeline).not.toHaveAttribute("open");
  const answer = screen.getByText(/Consider/).closest(".chat-message") as HTMLElement;
  expect(activity.compareDocumentPosition(answer) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(answer.querySelector(".katex")).not.toBeNull();
  await userEvent.click(within(activity).getByText("4 actions"));
  expect(timeline).toHaveAttribute("open");
  expect(within(activity).getByText("Read material")).toBeVisible();
  expect(within(activity).getByText("canvas/index.md")).toBeVisible();
  const details = screen.getByText("Session details").closest("details");
  expect(details).not.toHaveAttribute("open");
  await userEvent.click(screen.getByText("Session details"));
  expect(screen.getByText("openrouter/google/gemini-3.1-flash-lite")).toBeVisible();
});

it("shows one pending status and retains a user's disclosure choice across completion", async () => {
  const props = { model: null, onClose: vi.fn(), onSendMessage: vi.fn() };
  const { rerender } = renderWithI18n(
    <TutorDrawer
      {...props}
      messages={[
        {
          id: "pending",
          role: "agent",
          content: "Working through the lecture canvas...",
          isPending: true,
          toolTags: ["read: source.md"],
        },
      ]}
    />,
  );
  expect(screen.queryByText("Working through the lecture canvas...")).not.toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent("Working");
  expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  const summary = within(screen.getByLabelText("Tutor activity")).getByText("1 action");
  await userEvent.click(summary);
  const details = summary.closest("details");
  expect(details).toHaveAttribute("open");
  rerender(
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <TutorDrawer
        {...props}
        messages={[
          {
            id: "pending",
            role: "agent",
            content: "Here is the explanation.",
            toolTags: ["read: source.md"],
          },
        ]}
      />
    </I18nProvider>,
  );
  expect(details).toHaveAttribute("open");
  expect(screen.getByText("Here is the explanation.")).toBeVisible();
});

it("restores a failed message with an announced error for retry", async () => {
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
  await userEvent.type(composer, "Why is this wrong?");
  await userEvent.click(screen.getByRole("button", { name: "Send message" }));
  expect(composer).toBeDisabled();
  await act(async () =>
    rejectTurn(new Error("Provider credits exhausted. Retry after adding credits.")),
  );
  expect(screen.getByRole("alert")).toHaveTextContent("Provider credits exhausted");
  expect(composer).toHaveValue("Why is this wrong?");
  expect(composer).toBeEnabled();
});

it("supports multiline input and does not submit an IME composition", async () => {
  const onSendMessage = vi.fn().mockResolvedValue(undefined);
  renderWithI18n(
    <TutorDrawer messages={[]} model={null} onClose={vi.fn()} onSendMessage={onSendMessage} />,
  );
  const composer = screen.getByRole("textbox", { name: "Tutor message" });
  await userEvent.type(composer, "First line{Shift>}{Enter}{/Shift}Second line");
  expect(composer).toHaveValue("First line\nSecond line");
  fireEvent.keyDown(composer, { key: "Enter", isComposing: true });
  expect(onSendMessage).not.toHaveBeenCalled();
  await userEvent.keyboard("{Enter}");
  expect(onSendMessage).toHaveBeenCalledWith("First line\nSecond line");
});
