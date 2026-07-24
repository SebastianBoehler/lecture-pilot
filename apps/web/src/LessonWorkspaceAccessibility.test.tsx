import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { LessonWorkspace } from "./LessonWorkspace";
import type { LessonPanelMode } from "./types";

it("exposes and dismisses the active mobile lesson panel accessibly", async () => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      matches: true,
      media: "(max-width: 860px)",
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  );
  const user = userEvent.setup();
  render(<LessonWorkspaceHarness />);

  const outlineTrigger = screen.getByRole("button", { name: /open document outline/i });
  expect(outlineTrigger).toHaveAttribute("aria-controls", "lesson-panel");
  expect(outlineTrigger).toHaveAttribute("aria-expanded", "false");

  await user.click(outlineTrigger);

  expect(outlineTrigger).toHaveAttribute("aria-expanded", "true");
  const drawer = screen.getByRole("dialog", { name: /document outline panel/i });
  const closeButton = within(drawer).getByRole("button", { name: /close panel/i });
  expect(closeButton).toHaveFocus();
  await user.tab();
  expect(closeButton).toHaveFocus();

  await user.click(closeButton);

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(outlineTrigger).toHaveAttribute("aria-expanded", "false");
  await waitFor(() => expect(outlineTrigger).toHaveFocus());

  await user.click(outlineTrigger);
  expect(screen.getByRole("dialog", { name: /document outline panel/i })).toBeInTheDocument();

  await user.keyboard("{Escape}");

  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(outlineTrigger).toHaveAttribute("aria-expanded", "false");
  expect(outlineTrigger).toHaveFocus();
});

function LessonWorkspaceHarness() {
  const [panelMode, setPanelMode] = useState<LessonPanelMode | null>(null);
  return (
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <LessonWorkspace
        canvasDocument={null}
        canvasError={null}
        courseId="course-1"
        focusedSectionId="section-1"
        highlightedBlockId={null}
        highlightedText={null}
        lecture={{
          id: "lecture-1",
          number: "01",
          title: "Introduction",
          date: "2026-07-13",
          attendance: "unknown",
        }}
        messages={[]}
        navigationVersion={0}
        panelMode={panelMode}
        passedGateIds={[]}
        session={{ username: "student", term: "Summer 2026", courses: [] }}
        tutorModel={null}
        onResetWorkspace={vi.fn(async () => undefined)}
        onSendMessage={vi.fn(async () => undefined)}
        onTogglePanel={(mode) => setPanelMode((current) => (current === mode ? null : mode))}
      />
    </I18nProvider>
  );
}
