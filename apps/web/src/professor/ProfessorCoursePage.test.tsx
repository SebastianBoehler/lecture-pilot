import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  calls,
  courseWorkspace,
  json,
  lecture,
  mockApi,
  renderCoursePage,
  states,
} from "./coursePageTestFixtures";

afterEach(() => vi.unstubAllGlobals());

const everyState = states([
  lecture("lecture-01", { title: "Introduction" }),
  lecture("lecture-02", {
    title: "Gradient Descent",
    sources: "changed",
    goals: "stale",
    next_action: "keep_or_regenerate_goals",
  }),
  lecture("lecture-03", {
    title: "Regularization",
    published: false,
    sources: "new",
    goals: "needs_review",
    draft: "none",
    next_action: "review_goals",
  }),
  lecture("lecture-04", { title: "Kernels", goals: "proposing", next_action: "wait" }),
  lecture("lecture-05", { title: "Trees", draft: "generating", next_action: "wait" }),
  lecture("lecture-06", { title: "Ensembles", draft: "ready", next_action: "review_draft" }),
  lecture("lecture-07", {
    title: "Boosting",
    draft: "failed",
    draft_error: "Section 2 cites a page that is not in the sources.",
    next_action: "retry_draft",
  }),
  lecture("lecture-08", {
    title: "Clustering",
    published: false,
    draft: "none",
    next_action: "generate_draft",
  }),
  lecture("lecture-09", { title: "Mixtures", published: false, next_action: "confirm_routing" }),
]);

function row(title: string) {
  return screen.getByRole("rowheader", { name: new RegExp(title) }).closest("tr")!;
}

describe("Professor course page", () => {
  it("shows one status and at most one next step for every lecture state", async () => {
    mockApi({ "GET /lecture-states": () => json(everyState) });
    renderCoursePage();

    expect(await screen.findByRole("heading", { name: "Machine Learning" })).toBeInTheDocument();
    expect(screen.getByText("9 lectures, 6 published, 6 need your review")).toBeInTheDocument();
    const expected: [string, string, string | null][] = [
      ["Introduction", "Published", null],
      ["Gradient Descent", "Sources changed", "Check goals: Gradient Descent"],
      ["Regularization", "Goals to review", "Review goals: Regularization"],
      ["Kernels", "Proposing goals…", "Working…"],
      ["Trees", "Generating draft…", "Working…"],
      ["Ensembles", "Draft ready", "Review draft: Ensembles"],
      ["Boosting", "Draft failed", "Retry draft: Boosting"],
      ["Clustering", "Ready for a draft", "Generate draft: Clustering"],
      ["Mixtures", "File assignments to confirm", "Review file assignments: Mixtures"],
    ];
    for (const [title, status, action] of expected) {
      const cells = within(row(title));
      expect(cells.getByText(status)).toBeInTheDocument();
      const buttons = cells
        .queryAllByRole("button")
        .filter((button) => !button.textContent?.startsWith("Preview"));
      expect(
        buttons.map((button) => button.getAttribute("aria-label") ?? button.textContent),
      ).toEqual(action ? [action] : []);
    }
    expect(within(row("Kernels")).getByRole("button")).toBeDisabled();
    expect(within(row("Regularization")).getByText("New")).toBeInTheDocument();
    expect(
      within(row("Boosting")).getByText(
        "Why it failed: Section 2 cites a page that is not in the sources.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve & publish all ready (1)" })).toBeEnabled();
  });

  it("hands routing back to the builder and previews published lectures", async () => {
    mockApi({ "GET /lecture-states": () => json(everyState) });
    const user = userEvent.setup();
    const props = renderCoursePage();
    await user.click(await screen.findByRole("button", { name: /Review file assignments/ }));
    expect(props.onResumeCourse).toHaveBeenCalledWith(courseWorkspace);
    await user.click(screen.getByRole("button", { name: "Preview as student" }));
    expect(props.onPreviewLecture).toHaveBeenCalledWith(
      "machine-learning",
      courseWorkspace.lectures[0],
    );
  });

  it("starts a draft and shows the backend reason when it is refused", async () => {
    const fetchMock = mockApi({
      "GET /lecture-states": () => json(everyState),
      "POST /lectures/lecture-08/canvas/draft": () =>
        json({ detail: "Approve the learning goals for lecture 08 before drafting." }, 409),
      "POST /lectures/lecture-07/canvas/draft": () => json({ status: "running" }, 202),
    });
    const user = userEvent.setup();
    renderCoursePage();
    await user.click(await screen.findByRole("button", { name: "Generate draft: Clustering" }));
    expect(
      await within(row("Clustering")).findByText(
        "Approve the learning goals for lecture 08 before drafting.",
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Retry draft: Boosting" }));
    await waitFor(() =>
      expect(calls(fetchMock, "POST", "/lecture-07/canvas/draft")).toHaveLength(1),
    );
    const headers = new Headers(
      calls(fetchMock, "POST", "/lecture-07/canvas/draft")[0][1]?.headers,
    );
    expect(headers.get("Prefer")).toBe("respond-async");
    expect(headers.get("Idempotency-Key")).toMatch(/^[\w-]{16,}$/);
  });

  it("explains why lecture states could not be loaded", async () => {
    mockApi({ "GET /lecture-states": () => json({ detail: "Course not found." }, 404) });
    renderCoursePage();
    expect(await screen.findByRole("alert")).toHaveTextContent("Course not found.");
  });
});
