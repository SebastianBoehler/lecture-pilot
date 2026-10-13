import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { calls, json, lecture, mockApi, renderCoursePage, states } from "./coursePageTestFixtures";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";
import type { PracticeDesign } from "./practiceDesignTypes";

afterEach(() => vi.unstubAllGlobals());

function design(goals: [string, string, string][], approved: boolean, revision: string) {
  const base = practiceDesignFixture({
    courseId: "machine-learning",
    lectureId: "lecture-02",
    approvedBy: approved ? "prof" : null,
    revision,
  });
  const anchor = base.learning_intent.goals[0];
  return {
    ...base,
    learning_intent: {
      ...base.learning_intent,
      goals: goals.map(([id, title, outcome]) => ({ ...anchor, id, title, outcome })),
    },
  } satisfies PracticeDesign;
}

const approvedGoals = design(
  [
    ["g1", "Gradient steps", "Compute one gradient step."],
    ["g2", "Learning rate", "Explain the learning rate."],
    ["g3", "Momentum", "Describe momentum."],
  ],
  true,
  "a".repeat(64),
);
const regenerated = design(
  [
    ["g1", "Gradient steps", "Compute one gradient step."],
    ["g2", "Learning rate", "Choose a stable learning rate from a loss curve."],
    ["g9", "Line search", "Apply a backtracking line search."],
  ],
  false,
  "b".repeat(64),
);

const stale = lecture("lecture-02", {
  title: "Gradient Descent",
  sources: "changed",
  goals: "stale",
  next_action: "keep_or_regenerate_goals",
});

describe("Course page goal decisions", () => {
  it("keeps approved goals and starts the draft right away", async () => {
    let current = states([stale]);
    const fetchMock = mockApi({
      "GET /lecture-states": () => json(current),
      "GET /lectures/lecture-02/practice-design": () => json(approvedGoals),
      "GET /practice-design/intent/findings": () => json([]),
      "POST /practice-design/intent/keep": () => {
        current = states([{ ...stale, goals: "approved", next_action: "generate_draft" }]);
        return json(approvedGoals);
      },
      "POST /lectures/lecture-02/canvas/draft": () => {
        current = states([
          { ...stale, goals: "approved", draft: "generating", next_action: "wait" },
        ]);
        return json({ status: "running" }, 202);
      },
    });
    const user = userEvent.setup();
    renderCoursePage();
    await user.click(await screen.findByRole("button", { name: "Check goals: Gradient Descent" }));
    expect(
      await screen.findByRole("heading", {
        name: "Sources changed since you approved these goals",
      }),
    ).toBeInTheDocument();
    expect(await screen.findByText("Momentum")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Keep goals" }));

    expect(await screen.findByText("Generating draft…")).toBeInTheDocument();
    expect(calls(fetchMock, "POST", "/intent/keep")).toHaveLength(1);
    expect(calls(fetchMock, "POST", "/lecture-02/canvas/draft")).toHaveLength(1);
  });

  it("regenerates goals, compares them with the approved ones, and drafts after approval", async () => {
    let current = states([stale]);
    let saved: PracticeDesign = approvedGoals;
    const fetchMock = mockApi({
      "GET /lecture-states": () => json(current),
      "GET /lectures/lecture-02/practice-design": () => json(saved),
      "GET /practice-design/intent/findings": () => json([]),
      "POST /practice-design/intent/proposal": (_init, url) => {
        expect(url).toContain("refresh=true");
        saved = regenerated;
        current = states([{ ...stale, goals: "needs_review", next_action: "review_goals" }]);
        return json(regenerated);
      },
      "POST /practice-design/intent/approve": () => {
        current = states([
          { ...stale, goals: "approved", draft: "generating", next_action: "wait" },
        ]);
        return json({ ...regenerated, learning_intent: approvedGoals.learning_intent });
      },
      "POST /lectures/lecture-02/canvas/draft": () => json({ status: "running" }, 202),
    });
    const user = userEvent.setup();
    renderCoursePage();
    await user.click(await screen.findByRole("button", { name: "Check goals: Gradient Descent" }));
    await screen.findByText("Momentum");
    await user.click(screen.getByRole("button", { name: "Regenerate goals" }));

    const diff = await screen.findByRole("region", {
      name: "Compared with the goals you approved before",
    });
    const items = within(diff).getAllByRole("listitem");
    expect(items.map((item) => item.getAttribute("data-kind"))).toEqual([
      "kept",
      "changed",
      "added",
      "removed",
    ]);
    expect(within(items[1]).getByText("Explain the learning rate.").tagName).toBe("DEL");
    expect(within(items[3]).getByText("Momentum")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Approve learning goals" }));
    await waitFor(() =>
      expect(calls(fetchMock, "POST", "/lecture-02/canvas/draft")).toHaveLength(1),
    );
    expect(await screen.findByText("Generating draft…")).toBeInTheDocument();
  });

  it("shows why goals could not be kept", async () => {
    mockApi({
      "GET /lecture-states": () => json(states([stale])),
      "GET /lectures/lecture-02/practice-design": () => json(approvedGoals),
      "GET /practice-design/intent/findings": () => json([]),
      "POST /practice-design/intent/keep": () =>
        json({ detail: "These goals cite a source file that was removed." }, 409),
    });
    const user = userEvent.setup();
    renderCoursePage();
    await user.click(await screen.findByRole("button", { name: "Check goals: Gradient Descent" }));
    await screen.findByText("Momentum");
    await user.click(screen.getByRole("button", { name: "Keep goals" }));
    expect(
      await screen.findByText("These goals cite a source file that was removed."),
    ).toBeInTheDocument();
  });
});
