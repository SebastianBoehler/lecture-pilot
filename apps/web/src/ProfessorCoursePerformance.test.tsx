import { act, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProfessorCoursePerformance } from "./ProfessorCoursePerformance";
import { renderWithI18n } from "./test/renderWithI18n";

describe("ProfessorCoursePerformance", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("does not render zero-percent charts when a published lecture has no learner activity", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => json(noActivityAnalytics())),
    );

    renderWithI18n(
      <ProfessorCoursePerformance
        lectures={[lecture()]}
        publishedLectureIds={["lecture-01"]}
        session={session()}
        workspaceCourse={course()}
      />,
    );

    expect(await screen.findByText(/no learner signals yet/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("Lecture analytics chart")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /learning path gates/i })).not.toBeInTheDocument();
  });

  it("ignores a stale analytics failure after a newer request succeeds", async () => {
    const user = userEvent.setup();
    let rejectStaleRequest: (reason: Error) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockImplementationOnce(
          () =>
            new Promise((_, reject) => {
              rejectStaleRequest = reject;
            }),
        )
        .mockResolvedValueOnce(json(activityAnalytics("lecture-02"))),
    );

    renderWithI18n(
      <ProfessorCoursePerformance
        lectures={[lecture(), secondLecture()]}
        publishedLectureIds={["lecture-01", "lecture-02"]}
        session={session()}
        workspaceCourse={course()}
      />,
    );

    await user.click(screen.getByRole("button", { name: /second lecture/i }));
    expect(await screen.findAllByText("50%")).not.toHaveLength(0);
    await act(async () => {
      rejectStaleRequest(new TypeError("Failed to fetch"));
      await Promise.resolve();
    });
    expect(screen.queryByText(/cannot reach the local LecturePilot API/i)).not.toBeInTheDocument();
  });

  it("does not relabel a previous lecture's analytics while the next request is pending or fails", async () => {
    const user = userEvent.setup();
    let rejectNextRequest: (reason: Error) => void = () => undefined;
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(activityAnalytics("lecture-01")))
        .mockImplementationOnce(
          () =>
            new Promise((_, reject) => {
              rejectNextRequest = reject;
            }),
        ),
    );

    renderWithI18n(
      <ProfessorCoursePerformance
        lectures={[lecture(), secondLecture()]}
        publishedLectureIds={["lecture-01", "lecture-02"]}
        session={session()}
        workspaceCourse={course()}
      />,
    );

    expect(await screen.findAllByText("50%")).not.toHaveLength(0);
    await user.click(screen.getByRole("button", { name: /second lecture/i }));
    expect(screen.queryAllByText("50%")).toHaveLength(0);

    await act(async () => {
      rejectNextRequest(new TypeError("Failed to fetch"));
    });
    expect(await screen.findByText(/cannot reach the local LecturePilot API/i)).toBeInTheDocument();
    expect(screen.queryAllByText("50%")).toHaveLength(0);
  });
});

function json(payload: unknown) {
  return { ok: true, json: async () => payload };
}

function course() {
  return {
    id: "demo-ml-course",
    professor: "professor-demo",
    term: "Summer 2026",
    title: "Demo ML Course",
  };
}

function lecture() {
  return {
    attendance: "unknown" as const,
    date: "2026-05-09",
    id: "lecture-01",
    number: "01",
    title: "Introduction",
  };
}

function secondLecture() {
  return {
    attendance: "unknown" as const,
    date: "2026-05-16",
    id: "lecture-02",
    number: "02",
    title: "Second lecture",
  };
}

function noActivityAnalytics() {
  return {
    course_id: "demo-ml-course",
    gates: [],
    lecture_id: "lecture-01",
    quizzes: [],
    total_events: 0,
  };
}

function activityAnalytics(lectureId: string) {
  return {
    course_id: "demo-ml-course",
    gates: [],
    lecture_id: lectureId,
    quizzes: [
      {
        attendance_split: { present: 2 },
        component_id: "quiz-1",
        component_type: "quiz",
        correct_attempts: 1,
        correct_rate: 0.5,
        options: [],
        question: "Question",
        title: "Quiz",
        total_attempts: 2,
        unique_learners: 2,
      },
    ],
    total_events: 2,
  };
}

function session() {
  return {
    courses: [course()],
    roles: ["professor" as const],
    term: "Summer 2026",
    username: "professor-demo",
  };
}
