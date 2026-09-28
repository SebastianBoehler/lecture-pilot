import { act, renderHook } from "@testing-library/react";
import { expect, it } from "vitest";

import { practiceDesignFixture } from "./practiceDesignTestFixtures";
import { usePracticeDesignDrafts } from "./usePracticeDesignDrafts";

it("preserves unsaved goal edits when a new server revision arrives", () => {
  const full = practiceDesignFixture({ approvedBy: null });
  const target = full.targets[0];
  const design = {
    ...full,
    learning_intent: {
      source_revision: full.source_revision,
      objective: full.objective,
      planning_context: full.planning_context,
      revision: "i".repeat(64),
      approval: null,
      fixed_targets: [],
      goals: [
        {
          id: target.id,
          title: target.title,
          outcome: target.outcome,
          outcome_anchor: target.outcome_anchor,
          target_invariant: target.target_invariant,
          target_invariant_anchor: target.target_invariant_anchor,
        },
      ],
    },
  };
  const { result, rerender } = renderHook(usePracticeDesignDrafts, {
    initialProps: { designs: { [design.lecture_id]: design }, lectureIds: [design.lecture_id] },
  });
  const edited = {
    ...design,
    learning_intent: {
      ...design.learning_intent,
      goals: [{ ...design.learning_intent.goals[0], title: "Professor's revision" }],
    },
  };
  act(() => result.current.change(design.lecture_id, edited));
  rerender({
    designs: { [design.lecture_id]: { ...design, revision: "n".repeat(64) } },
    lectureIds: [design.lecture_id],
  });
  expect(result.current.drafts[design.lecture_id]).toEqual(edited);
  expect(result.current.conflicts[design.lecture_id]).toBe(true);
});
