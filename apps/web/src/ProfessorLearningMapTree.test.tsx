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
      name: /decision making.*100% passed/i,
    });
    expect(rootToggle).toHaveAttribute("aria-expanded", "false");

    const rootItem = rootToggle.closest("li");
    const branch = rootItem?.querySelector(":scope > .learning-map-branch");
    expect(branch?.querySelectorAll(":scope > li")).toHaveLength(2);

    await user.click(rootToggle);
    expect(rootToggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText(/risk evidence gate/i)).toBeInTheDocument();
    expect(screen.getAllByText(/100% passed/i)).toHaveLength(2);
    expect(screen.getByText(/1\/1 checks/i)).toBeInTheDocument();

    const bayesToggle = within(tree).getByRole("button", { name: /bayes formula/i });
    await user.click(bayesToggle);
    expect(screen.getByText(/unlocks after decision making/i)).toBeInTheDocument();
  });
});

function analytics(): LectureAnalyticsSummary {
  return {
    course_id: "demo-ml-course",
    lecture_id: "lecture-03",
    total_events: 1,
    quizzes: [],
    gates: [
      {
        gate_id: "risk-gate",
        total_events: 1,
        unique_learners: 1,
        status_counts: { passed: 1 },
        attendance_split: { present: 1 },
        independent_attempts: 1,
        independent_passes: 1,
        supported_attempts: 0,
        transfer_attempts: 0,
        independent_transfer_passes: 0,
        assistance_level_counts: { none: 1 },
        evidence_counts: {},
      },
    ],
    learning_map: {
      course_id: "demo-ml-course",
      lecture_id: "lecture-03",
      title: "Bayesian Decision Theory",
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
          evidence_required: "Connect posterior and loss.",
          section_id: "aim",
          source_ref: "Lecture03-eng.tex#aim",
        },
      ],
    },
  };
}
