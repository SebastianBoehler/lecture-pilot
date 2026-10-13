import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { calls, json, lecture, mockApi, renderCoursePage, states } from "./coursePageTestFixtures";
import type { CanvasDocument, CanvasSection } from "../shared/types";

afterEach(() => vi.unstubAllGlobals());

const section = (id: string, title: string, texts: string[]): CanvasSection => ({
  id,
  title,
  blocks: texts.map((text, index) => ({
    id: `${id}-${index}`,
    type: "paragraph",
    text,
    items: [],
  })),
});
const canvas = (lectureId: string, sections: CanvasSection[]): CanvasDocument => ({
  id: `canvas-${lectureId}`,
  course_id: "machine-learning",
  lecture_id: lectureId,
  title: "Ensembles",
  source_kind: "generated",
  source_ref: "source",
  sections,
});
const approval = {
  draft_digest: "d".repeat(64),
  source_revision: "s".repeat(64),
  practice_design_revision: "p".repeat(64),
  learning_map_revision: "map-2",
};
const review = { ...approval, learning_map: { revision: approval.learning_map_revision } };
const ready = (id: string, title: string) =>
  lecture(id, { title, draft: "ready", next_action: "review_draft" });

describe("Course page draft review", () => {
  it("shows section changes against the published version and publishes on approval", async () => {
    let current = states([ready("lecture-06", "Ensembles")]);
    const fetchMock = mockApi({
      "GET /lecture-states": () => json(current),
      "GET /admin/courses/machine-learning/lectures/lecture-06/canvas/draft": () =>
        json(
          canvas("lecture-06", [
            section("intro", "Why ensembles", ["Many weak models vote."]),
            section("bagging", "Bagging", ["Bootstrap samples.", "Average the votes."]),
            section("stacking", "Stacking", ["Learn how to combine models."]),
          ]),
        ),
      "GET /courses/machine-learning/lectures/lecture-06/canvas": () =>
        json({
          publication_version: 1,
          learning_map_revision: "map-1",
          document: canvas("lecture-06", [
            section("intro", "Why ensembles", ["Many weak models vote."]),
            section("bagging", "Bagging", ["Bootstrap samples.", "Take the majority."]),
            section("history", "History", ["Old notes."]),
          ]),
        }),
      "GET /lectures/lecture-06/canvas/learning-design": () => json(review),
      "POST /lectures/lecture-06/canvas/publish": (init) => {
        expect(JSON.parse(String(init?.body))).toEqual(approval);
        current = states([lecture("lecture-06", { title: "Ensembles" })]);
        return json({ course_id: "machine-learning", lecture_id: "lecture-06", published: true });
      },
    });
    const user = userEvent.setup();
    const props = renderCoursePage();
    await user.click(await screen.findByRole("button", { name: "Review draft: Ensembles" }));

    const changed = (await screen.findByText("Bagging")).closest("article")!;
    expect(within(changed).getByText("Changed section")).toBeInTheDocument();
    expect((await within(changed).findByText("Take the majority.")).closest("del")).not.toBeNull();
    expect((await within(changed).findByText("Average the votes.")).closest("ins")).not.toBeNull();
    expect(screen.getByText("Stacking").closest("article")).toHaveAttribute("data-kind", "added");
    expect(screen.getByText("History").closest("article")).toHaveAttribute("data-kind", "removed");
    expect(screen.getByText("1 unchanged")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open full draft preview" })).toHaveAttribute(
      "href",
      "/professor/courses/machine-learning/lectures/lecture-06/draft",
    );

    await user.click(screen.getByRole("button", { name: "Approve & publish" }));
    expect(await screen.findByText("Published")).toBeInTheDocument();
    expect(calls(fetchMock, "POST", "/lecture-06/canvas/publish")).toHaveLength(1);
    expect(props.onCourseChanged).toHaveBeenCalled();
  });

  it("approves and publishes every ready draft, keeping each failure on its lecture", async () => {
    let current = states([
      ready("lecture-02", "Gradient Descent"),
      ready("lecture-03", "Regularization"),
      lecture("lecture-04", {
        title: "Kernels",
        goals: "needs_review",
        next_action: "review_goals",
      }),
    ]);
    const fetchMock = mockApi({
      "GET /lecture-states": () => json(current),
      "GET /canvas/learning-design": () => json(review),
      "POST /lectures/lecture-02/canvas/publish": () => {
        current = states([
          lecture("lecture-02", { title: "Gradient Descent" }),
          current.lectures[1],
          current.lectures[2],
        ]);
        return json({ published: true });
      },
      "POST /lectures/lecture-03/canvas/publish": () =>
        json({ detail: "The draft changed after review. Review it again." }, 409),
    });
    const user = userEvent.setup();
    renderCoursePage();
    await user.click(
      await screen.findByRole("button", { name: "Approve & publish all ready (2)" }),
    );
    await waitFor(() => expect(calls(fetchMock, "POST", "/canvas/publish")).toHaveLength(2));
    const failed = screen.getByRole("rowheader", { name: /Regularization/ });
    expect(
      await within(failed).findByText("The draft changed after review. Review it again."),
    ).toBeInTheDocument();
    expect(calls(fetchMock, "POST", "/lecture-04/canvas/publish")).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Approve & publish all ready (1)" })).toBeEnabled();
  });
});
