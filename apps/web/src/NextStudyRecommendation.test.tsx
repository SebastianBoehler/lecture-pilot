import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { NextStudyRecommendation } from "./NextStudyRecommendation";
import { renderWithI18n } from "./test/renderWithI18n";
import type { Lecture, UniversityCourse } from "./types";

const candidateLectures: Lecture[] = [
  {
    id: "lecture-01",
    number: "01",
    title: "Foundations",
    date: "2026-04-01",
    attendance: "present",
  },
  {
    id: "lecture-02",
    number: "02",
    title: "Generalization",
    date: "2026-04-08",
    attendance: "absent",
  },
  { id: "lecture-03", number: "03", title: "Bayes", date: "2026-04-15", attendance: "unknown" },
];

const course: UniversityCourse = {
  access_policy: "tuebingen_enrolled",
  id: "software-quality",
  title: "Softwarequalität in Theorie und Industrieller Praxis",
  professor: "University of Tübingen",
  term: "Sommer 2026",
};

describe("NextStudyRecommendation", () => {
  it("prioritizes an unpassed missed lecture and opens it", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    renderWithI18n(
      <NextStudyRecommendation
        course={course}
        lectures={candidateLectures}
        passedLectureIds={["lecture-01"]}
        onOpen={onOpen}
      />,
    );

    expect(screen.getByRole("heading", { name: /next study step/i })).toBeInTheDocument();
    expect(screen.queryByText(/based on your progress/i)).not.toBeInTheDocument();
    expect(screen.getByText(course.title)).toBeInTheDocument();
    expect(screen.getByText("02 · Generalization")).toBeInTheDocument();
    expect(screen.getByText(/missed this lecture/i)).toBeInTheDocument();
    expect(screen.getByText("Start learning")).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", {
        name: `Start recommended lecture 02 in ${course.title}`,
      }),
    );
    expect(onOpen).toHaveBeenCalledWith(candidateLectures[1]);
  });

  it("prioritizes a due gate review over readiness and attendance continuation", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    const onOpenGateReview = vi.fn();
    renderWithI18n(
      <NextStudyRecommendation
        course={course}
        lectures={candidateLectures}
        passedLectureIds={[]}
        reviewQueue={{
          course_id: course.id,
          items: [
            {
              id: "gate:lecture-03:risk-check",
              kind: "gate_review",
              course_id: course.id,
              lecture_id: "lecture-03",
              lecture_title: "Bayes",
              section_id: "risk",
              section_title: "Risk transfer",
              gate_id: "risk-check",
              gate_revision: "revision-1",
              due_at: "2026-08-08T10:00:00+00:00",
            },
            {
              id: "readiness:repair-risk",
              kind: "readiness_repair",
              course_id: course.id,
              lecture_id: "lecture-02",
              lecture_title: "Generalization",
              section_id: "bounds",
              section_title: "Bounds",
              task_id: "repair-risk",
              next_action: "Revisit the generalization bound.",
            },
          ],
        }}
        onOpen={onOpen}
        onOpenGateReview={onOpenGateReview}
      />,
    );

    expect(screen.getByText("Risk transfer")).toBeInTheDocument();
    expect(screen.getByText(/delayed transfer check is due/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /open due review/i }));
    expect(onOpenGateReview).toHaveBeenCalledWith(
      expect.objectContaining({ gate_id: "risk-check", lecture_id: "lecture-03" }),
    );
    expect(onOpen).not.toHaveBeenCalled();
  });

  it("shows a readiness task's evidence-driven next action before attendance continuation", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    renderWithI18n(
      <NextStudyRecommendation
        course={course}
        lectures={candidateLectures}
        passedLectureIds={[]}
        reviewQueue={{
          course_id: course.id,
          items: [
            {
              id: "readiness:repair-risk",
              kind: "readiness_repair",
              course_id: course.id,
              lecture_id: "lecture-02",
              lecture_title: "Generalization",
              section_id: "bounds",
              section_title: "Bounds",
              task_id: "repair-risk",
              next_action: "Revisit the generalization bound and explain the weak point.",
            },
          ],
        }}
        onOpen={onOpen}
      />,
    );

    expect(
      screen.getByText("Revisit the generalization bound and explain the weak point."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /open readiness repair/i }));
    expect(onOpen).toHaveBeenCalledWith(candidateLectures[1]);
  });
});
