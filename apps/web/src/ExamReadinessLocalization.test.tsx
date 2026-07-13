import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ExamReadinessPanel } from "./ExamReadinessPanel";
import { renderWithI18n } from "./test/renderWithI18n";
import type { Lecture, LoginSession, UniversityCourse } from "./types";

describe("Exam readiness localization", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("keeps course text intact inside a German rubric-review flow", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) =>
        json(init?.method === "POST" ? attemptPayload() : checkPayload()),
      ),
    );
    renderWithI18n(
      <ExamReadinessPanel
        course={course}
        lectures={[lecture]}
        session={session}
        onOpenLecture={vi.fn()}
      />,
      { locale: "de" },
    );

    expect(screen.getByRole("heading", { name: "Prüfungscheck" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Prüfungscheck starten" }));

    const dialog = await screen.findByRole("dialog", { name: "Prüfungscheck" });
    expect(within(dialog).queryByRole("main")).not.toBeInTheDocument();
    expect(within(dialog).queryByText("Prüfungsvorbereitung")).not.toBeInTheDocument();
    expect(within(dialog).getByText("Explain the source concept.")).toHaveFocus();
    await user.type(
      within(dialog).getByLabelText("Deine Antwort im Prüfungsstil"),
      "Eine kurze Antwort.",
    );
    await user.click(within(dialog).getByRole("button", { name: "Bereitschaft prüfen" }));

    expect(
      await within(dialog).findByRole("heading", { name: "Rubrikprüfung ausstehend" }),
    ).toHaveFocus();
    expect(within(dialog).queryByText("Dein Ergebnis")).not.toBeInTheDocument();
    expect(within(dialog).queryByText("Nächste Schritte")).not.toBeInTheDocument();
    expect(within(dialog).queryByRole("heading", { name: "Weiter üben" })).not.toBeInTheDocument();
    expect(within(dialog).getByText("Ausstehend")).toBeInTheDocument();
    expect(within(dialog).getByText("Review the source concept.")).toBeInTheDocument();
    expect(within(dialog).getByRole("list", { name: "Ergebnisübersicht" })).toHaveTextContent(
      "1 Priorität",
    );
  });
});

const session: LoginSession = {
  username: "student01",
  term: "Sommer 2026",
  roles: ["student"],
  courses: [],
};

const course: UniversityCourse = {
  id: "martius-ml",
  title: "Grundlagen des Maschinellen Lernens",
  professor: "Prof. Georg Martius",
  term: "Sommer 2026",
};

const lecture: Lecture = {
  id: "lecture-03",
  number: "03",
  title: "Bayesian Decision Theory",
  date: "2026-04-29",
  attendance: "unknown",
};

function checkPayload() {
  return {
    course_id: course.id,
    passing_score: 0.7,
    published_lecture_count: 1,
    coverage: [],
    questions: [
      {
        id: "question-1",
        kind: "open_ended",
        lecture_id: lecture.id,
        lecture_title: lecture.title,
        section_id: "source-concept",
        section_title: "Source concept",
        prompt: "Explain the source concept.",
        options: [],
      },
    ],
  };
}

function attemptPayload() {
  return {
    course_id: course.id,
    passing_score: 0.7,
    score: null,
    guidance_level: "standard",
    results: [
      {
        question_id: "question-1",
        kind: "open_ended",
        lecture_id: lecture.id,
        section_id: "source-concept",
        answer_kind: "open_ended",
        correct: null,
        status: "needs_rubric_review",
      },
    ],
    tasks: [
      {
        id: "question-1-review",
        question_id: "question-1",
        kind: "review_open_answer",
        status: "open",
        guidance_level: "standard",
        lecture_id: lecture.id,
        lecture_title: lecture.title,
        section_id: "source-concept",
        section_title: "Source concept",
        prompt: "Explain the source concept.",
        rubric: ["Use source evidence."],
        expected_evidence: "Use source evidence.",
        next_action: "Review the source concept.",
        scaffold_policy: {
          trigger: "readiness_task",
          learner_stage: "novice",
          profile: "worked_example",
          process_label: "scaffolded_reasoning",
          tutor_move: "Ask for evidence.",
          forbidden: "Reveal the answer.",
        },
      },
    ],
  };
}

function json(payload: unknown) {
  return {
    ok: true,
    json: async () => payload,
  };
}
