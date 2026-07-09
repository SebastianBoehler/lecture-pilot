import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProfessorLearningMapTree } from "./ProfessorLearningMapTree";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LectureAnalyticsSummary } from "./types";

describe("ProfessorLearningMapTree", () => {
  it("shows gate pass rates by learning path node", () => {
    renderWithI18n(<ProfessorLearningMapTree analytics={analytics()} />);

    expect(screen.getByRole("heading", { name: /learning path gates/i })).toBeInTheDocument();
    expect(screen.getByText(/risk evidence gate/i)).toBeInTheDocument();
    expect(screen.getByText(/100% passed/i)).toBeInTheDocument();
    expect(screen.getByText(/1\/1 checks/i)).toBeInTheDocument();
    expect(screen.getByText(/unlocks after aim/i)).toBeInTheDocument();
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
