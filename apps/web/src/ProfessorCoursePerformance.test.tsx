import { act, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ProfessorCoursePerformance } from "./ProfessorCoursePerformance";
import {
  activityAnalytics,
  course,
  courseActivityAnalytics,
  json,
  lecture,
  noActivityAnalytics,
  noActivityCourse,
  secondLecture,
  session,
} from "./ProfessorCoursePerformance.testFixtures";
import { renderWithI18n } from "./test/renderWithI18n";

describe("ProfessorCoursePerformance", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("opens with a course overview and drills into a selected lecture", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        json(
          String(input).includes("/lectures/")
            ? activityAnalytics("lecture-01")
            : courseActivityAnalytics(),
        ),
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

    expect(await screen.findByRole("heading", { name: /course overview/i })).toBeInTheDocument();
    expect(screen.getByText("3", { selector: ".analytics-kpi strong" })).toBeInTheDocument();
    await user.click(lectureButton(/introduction/i));
    expect(await screen.findByRole("heading", { name: "Introduction" })).toBeInTheDocument();
  });

  it("does not render zero-percent charts when a published lecture has no learner activity", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        json(String(input).includes("/lectures/") ? noActivityAnalytics() : noActivityCourse()),
      ),
    );

    renderWithI18n(
      <ProfessorCoursePerformance
        lectures={[lecture()]}
        publishedLectureIds={["lecture-01"]}
        session={session()}
        workspaceCourse={course()}
      />,
    );

    await userEvent.setup().click(lectureButton(/introduction/i));
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
        .mockResolvedValueOnce(json(courseActivityAnalytics()))
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

    await screen.findByRole("heading", { name: /course overview/i });
    await user.click(lectureButton(/introduction/i));
    await user.click(lectureButton(/second lecture/i));
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
        .mockResolvedValueOnce(json(courseActivityAnalytics()))
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

    await screen.findByRole("heading", { name: /course overview/i });
    await user.click(lectureButton(/introduction/i));
    expect(await screen.findAllByText("50%")).not.toHaveLength(0);
    await user.click(lectureButton(/second lecture/i));
    expect(screen.queryAllByText("50%")).toHaveLength(0);

    await act(async () => {
      rejectNextRequest(new TypeError("Failed to fetch"));
    });
    expect(await screen.findByText(/cannot reach the local LecturePilot API/i)).toBeInTheDocument();
    expect(screen.queryAllByText("50%")).toHaveLength(0);
  });

  it("keeps lecture selection and evidence views explicit", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) =>
        json(
          String(input).includes("/lectures/")
            ? activityAnalytics("lecture-01")
            : courseActivityAnalytics(),
        ),
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

    await screen.findByRole("heading", { name: /course overview/i });
    await userEvent.setup().click(lectureButton(/introduction/i));
    expect(await screen.findByRole("heading", { name: "Introduction" })).toBeInTheDocument();
    expect(lectureButton(/introduction/i)).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("tab", { name: /quiz friction.*1/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tab", { name: /gate evidence.*0/i })).toBeDisabled();
    expect(screen.queryByLabelText("Lecture analytics chart")).not.toBeInTheDocument();
  });
});

function lectureButton(name: RegExp) {
  return within(screen.getByRole("navigation", { name: /performance lecture list/i })).getByRole(
    "button",
    { name },
  );
}
