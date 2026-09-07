import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import { learningDesignPayload } from "./testLearningDesignReviewFixture";
import { openProfessorDemo } from "./testLessonActions";

afterEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  vi.unstubAllGlobals();
});

it("reloads exact-draft approvals when another lecture changes but ready statuses do not", async () => {
  const user = userEvent.setup();
  window.sessionStorage.setItem(
    "lecturepilot.professor-builder.current",
    JSON.stringify({
      bundleReady: true,
      canvasReady: true,
      courseReady: true,
      lectureSchedule: [],
      query: "",
      setup: {
        accessPolicy: "tuebingen_enrolled",
        canvasLanguage: "en",
        courseTitle: "Demo ML Course",
        firstLectureDate: "2026-04-14",
        lectureCount: "2",
        lectureNumber: "",
        lectureTitle: "",
        target: "full-course",
      },
      workspace: { courseId: "demo-ml-course", lectureId: "lecture-01" },
    }),
  );
  const base = professorFetchMock();
  let changed = false;
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string, init?: RequestInit) => {
      if (url.includes("/canvas/learning-design") && !init?.method) {
        const lecture = url.includes("lecture-02") ? "lecture-02" : "lecture-01";
        return Promise.resolve(
          new Response(
            JSON.stringify(
              learningDesignPayload(
                "demo-ml-course",
                lecture,
                !(changed && lecture === "lecture-02"),
              ),
            ),
          ),
        );
      }
      return base(url, init);
    }),
  );
  render(<App />);
  await openProfessorDemo(user);
  expect(await screen.findByText("2 of 2 approved")).toBeVisible();
  changed = true;
  await user.click(screen.getByRole("button", { name: "Refresh workspace state" }));
  expect(await screen.findByText("1 of 2 approved")).toBeVisible();
});
