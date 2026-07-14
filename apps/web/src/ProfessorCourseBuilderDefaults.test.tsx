import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import { openProfessorDemo } from "./testLessonActions";

describe("Professor course builder defaults", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("does not restore the old canned lecture 03 demo defaults for a fresh builder", async () => {
    const user = userEvent.setup();
    window.sessionStorage.setItem(
      "lecturepilot.professor-builder.current",
      JSON.stringify({
        setup: {
          accessPolicy: "tuebingen_enrolled",
          courseTitle: "Grundlagen des Maschinellen Lernens",
          lectureTitle: "Bayesian Decision Theory",
          lectureNumber: "03",
          lectureCount: "",
          firstLectureDate: "2026-05-06",
          target: "single-lecture",
        },
        workspace: null,
        courseReady: false,
        bundleReady: false,
        canvasReady: false,
        lectureSchedule: [],
        query: "Bayesian decision theory machine learning Tübingen",
      }),
    );
    vi.stubGlobal("fetch", professorFetchMock());
    render(<App />);

    await openProfessorDemo(user);

    expect(screen.getByLabelText(/course name/i)).toHaveValue("");
    expect(screen.getByLabelText(/course name/i)).toHaveAccessibleDescription(
      /exact course title from alma or ilias.*course title and term/i,
    );
    expect(screen.queryByLabelText(/lecture title/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /full course/i })).toHaveClass("is-active");
    expect(screen.getByRole("button", { name: /create course workspace/i })).toBeDisabled();
  });

  it("does not restore old full-course demo defaults without a created workspace", async () => {
    const user = userEvent.setup();
    window.sessionStorage.setItem(
      "lecturepilot.professor-builder.current",
      JSON.stringify({
        setup: {
          accessPolicy: "tuebingen_enrolled",
          courseTitle: "Grundlagen des Maschinellen Lernens",
          lectureTitle: "",
          lectureNumber: "",
          lectureCount: "",
          firstLectureDate: "2026-06-07",
          target: "full-course",
        },
        workspace: null,
        courseReady: false,
        bundleReady: false,
        canvasReady: false,
        lectureSchedule: [],
        query: "",
      }),
    );
    vi.stubGlobal("fetch", professorFetchMock());
    render(<App />);

    await openProfessorDemo(user);

    expect(screen.getByLabelText(/course name/i)).toHaveValue("");
    expect(screen.getByLabelText(/first lecture date/i)).toHaveValue("");
    expect(screen.getByRole("button", { name: /full course/i })).toHaveClass("is-active");
    expect(screen.getByRole("button", { name: /create course workspace/i })).toBeDisabled();
  });

  it("shows a backend reachability error when course workspace creation cannot reach the API", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    render(<App />);

    await openProfessorDemo(user);
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));

    expect(
      await screen.findByText(
        /cannot reach the local lecturepilot api while creating the course workspace/i,
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/^Failed to fetch$/i)).not.toBeInTheDocument();
  });
});
