import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { OutlinePanel } from "./LessonSidePanels";
import type { CanvasDocument } from "./types";

afterEach(() => vi.restoreAllMocks());

it("distinguishes checks by task and shortens provenance without losing its full caption", async () => {
  const onJumpAnchor = vi.fn();
  render(
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <OutlinePanel
        activeAnchorId={null}
        onClose={vi.fn()}
        onJumpAnchor={onJumpAnchor}
        canvasDocument={
          {
            id: "course-lecture",
            course_id: "course",
            lecture_id: "lecture",
            title: "Classification",
            source_kind: "generated",
            source_ref: "lecture.pdf",
            sections: [
              {
                id: "concept",
                title: "Classification",
                blocks: [
                  {
                    id: "check",
                    type: "checkpoint",
                    caption: "Checkpoint",
                    text: "Explain why unseen examples matter for classification.",
                    items: [],
                  },
                  {
                    id: "slide",
                    type: "asset",
                    caption: "Original slide 14 from uploads/private/lecture.pdf",
                    items: [],
                  },
                  {
                    id: "second-check",
                    type: "checkpoint",
                    caption: "Compare the classifiers",
                    text: "Compare two classifiers on the given observations.",
                    items: [],
                  },
                ],
              },
            ],
          } satisfies CanvasDocument
        }
      />
    </I18nProvider>,
  );

  await userEvent.click(
    screen.getByRole("button", { name: "Explain why unseen examples matter for" }),
  );
  expect(onJumpAnchor).toHaveBeenCalledWith("check");
  await userEvent.click(screen.getByRole("button", { name: "Compare the classifiers" }));
  expect(onJumpAnchor).toHaveBeenLastCalledWith("second-check");
  expect(screen.getByRole("button", { name: "Original slide 14" })).toHaveAttribute(
    "title",
    "Original slide 14 from uploads/private/lecture.pdf",
  );
});
