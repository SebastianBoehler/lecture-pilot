import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ProfessorLearningMapTree } from "./ProfessorLearningMapTree";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LectureAnalyticsSummary } from "./types";

describe("ProfessorLearningMapTree", () => {
  it("shows an expandable prerequisite tree with gate states", async () => {
    const user = userEvent.setup();
    renderWithI18n(<ProfessorLearningMapTree analytics={analytics()} />);

    expect(screen.getByRole("heading", { name: /learning path gates/i })).toBeInTheDocument();
    const tree = screen.getByRole("list", {
      name: /bayesian decision theory learning path gates/i,
    });
    const rootToggle = within(tree).getByRole("button", {
      name: /decision making.*evidence available/i,
    });
    expect(rootToggle).toHaveAttribute("aria-expanded", "false");

    const rootItem = rootToggle.closest("li");
    const branch = rootItem?.querySelector(":scope > .learning-map-branch");
    expect(branch?.querySelectorAll(":scope > li")).toHaveLength(2);

    await user.click(rootToggle);
    expect(rootToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/risk evidence gate/i)).toBeInTheDocument();
    expect(screen.getByText(/60% independent first pass/i)).toBeInTheDocument();
    expect(screen.getByText(/5 activity events/i)).toBeInTheDocument();

    const bayesToggle = within(tree).getByRole("button", { name: /bayes formula/i });
    await user.click(bayesToggle);
    expect(screen.getByText(/unlocks after decision making/i)).toBeInTheDocument();
  });
});

function analytics(): LectureAnalyticsSummary {
  return {
    course_id: "demo-ml-course",
    lecture_id: "lecture-03",
    activity_events: 1,
    unique_learners: 5,
    current_publication_version: 1,
    current_learning_map_revision: "map-1",
    correction_after_feedback: cell("correction_after_feedback", 0, null),
    delayed_transfer: cell("delayed_transfer", 0, null),
    independent_first_pass: cell("independent_first_pass", 5, 0.6),
    quizzes: [],
    quiz_first_attempt: cell("quiz_first_attempt", 0, null),
    supported_retry: cell("supported_retry", 0, null),
    gates: [
      {
        gate_id: "risk-gate",
        activity_events: 5,
        unique_learners: 5,
        publication_version: 1,
        gate_revision: "revision-1",
        learning_map_revision: "map-1",
        version_status: "current",
        independent_first_pass: {
          evidence_type: "independent_first_pass",
          sample_size: 5,
          data_status: "available",
          rate: 0.6,
        },
        supported_retry: {
          evidence_type: "supported_retry",
          sample_size: 0,
          data_status: "insufficient_data",
          rate: null,
        },
        delayed_transfer: {
          evidence_type: "delayed_transfer",
          sample_size: 0,
          data_status: "insufficient_data",
          rate: null,
        },
      },
    ],
    learning_map: {
      course_id: "demo-ml-course",
      lecture_id: "lecture-03",
      title: "Bayesian Decision Theory",
      objective: "Explain and apply Bayesian decision theory.",
      revision: "b".repeat(64),
      nodes: [
        {
          id: "aim",
          title: "Decision making",
          lecture_id: "lecture-03",
          section_id: "aim",
          source_ref: "Lecture03-eng.tex#aim",
          prerequisites: [],
          gate_ids: ["risk-gate"],
          quiz_ids: [],
        },
        {
          id: "bayes-formula",
          title: "Bayes formula",
          lecture_id: "lecture-03",
          section_id: "bayes-formula",
          source_ref: null,
          prerequisites: ["aim"],
          gate_ids: [],
          quiz_ids: ["risk-check"],
        },
        {
          id: "losses",
          title: "Loss decisions",
          lecture_id: "lecture-03",
          section_id: "losses",
          source_ref: null,
          prerequisites: ["aim"],
          gate_ids: [],
          quiz_ids: [],
        },
      ],
      gates: [
        {
          id: "risk-gate",
          concept_id: "aim",
          title: "Risk evidence gate",
          prompt: "Explain expected risk.",
          evidence_criteria: [
            { id: "risk", description: "Connect posterior and loss.", required: true },
          ],
          transfer_prompt: "Apply expected risk to a changed case.",
          review_after_days: 2,
          revision: "a".repeat(64),
          section_id: "aim",
          source_ref: "Lecture03-eng.tex#aim",
        },
      ],
    },
  };
}

function cell(evidenceType: string, sampleSize: number, rate: number | null) {
  return {
    data_status: rate === null ? ("insufficient_data" as const) : ("available" as const),
    evidence_type: evidenceType,
    rate,
    sample_size: sampleSize,
  };
}
