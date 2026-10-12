import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";
import { previewLectures } from "./dashboardLectureProgress";
import { renderWithI18n } from "../test/renderWithI18n";
import type { Lecture, LoginSession, UniversityCourse } from "../shared/types";
import type { LearnerProfileState } from "../profile/useLearnerProfile";

afterEach(() => vi.unstubAllGlobals());

const course: UniversityCourse = {
  id: "progress-course",
  title: "Progress course",
  professor: "Professor",
  term: "2026",
};

const lectures: Lecture[] = [
  lecture("lecture-01", "01", "2026-04-01"),
  lecture("lecture-02", "02", "2026-04-08"),
  lecture("lecture-03", "03", "2026-04-15"),
  {
    ...lecture("lecture-04", "04", "2099-04-22"),
    releaseStatus: "scheduled",
    effectivePublicationAt: "2099-04-22T08:00:00Z",
  },
];

const session: LoginSession = {
  username: "student-a",
  tenant_id: "tenant-tuebingen",
  term: "2026",
  roles: ["student"],
  courses: [course],
};

describe("Dashboard study progress", () => {
  it("shows course and lecture progress, new badges, and records an opened lecture", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/courses/progress-course/visits") && init?.method === "POST") {
        return json({ course_id: course.id, new_lecture_ids: ["lecture-03"] });
      }
      if (url.endsWith("/visits")) return new Response(null, { status: 204 });
      return json({ course_id: course.id, items: [], upcoming: [] });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWithI18n(
      <Dashboard
        learnerProfileState={profileState()}
        lectures={lectures}
        publishedLectureIds={lectures.map((item) => item.id)}
        session={session}
        workspaceCourse={course}
        onOpen={onOpen}
        onSetAttendance={vi.fn()}
      />,
    );

    expect(screen.getByText("33% complete · 1 of 3 lectures")).toBeVisible();
    await user.click(screen.getByRole("button", { name: /show all 4 lectures/i }));
    expect(within(row("Lecture 01")).getByText("Completed")).toBeVisible();
    expect(within(row("Lecture 02")).getByText("1/3 checks")).toBeVisible();
    const newRow = row("Lecture 03");
    expect(await within(newRow).findByText("New")).toHaveAttribute(
      "title",
      "Published since your last visit",
    );
    expect(within(row("Lecture 04")).queryByText("New")).not.toBeInTheDocument();

    await user.click(within(newRow).getByRole("button", { name: /open lecture 03/i }));

    expect(onOpen).toHaveBeenCalledWith(course.id, lectures[2]);
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/courses/progress-course/lectures/lecture-03/visits"),
        expect.objectContaining({ method: "POST" }),
      ),
    );
    expect(within(row("Lecture 03")).queryByText("New")).not.toBeInTheDocument();
  });

  it("previews the newest unlocked lectures first and the next scheduled one", () => {
    expect(previewLectures(lectures, 2).map((item) => item.id)).toEqual([
      "lecture-03",
      "lecture-02",
      "lecture-04",
    ]);
  });
});

function row(title: string) {
  return screen.getByRole("heading", { name: title }).closest("article") as HTMLElement;
}

function lecture(id: string, number: string, date: string): Lecture {
  return {
    id,
    number,
    title: `Lecture ${number}`,
    date,
    attendance: "present",
    contentReady: true,
    releaseStatus: "released",
    unlocked: true,
  };
}

function profileState(): LearnerProfileState {
  return {
    profile: {
      onboarding_completed: true,
      preferences: {},
      global_notes: "",
      global_files: [],
      courses: [
        {
          course_id: course.id,
          memory: "",
          files: [],
          passed_lecture_ids: ["lecture-01"],
          lecture_progress: [
            { lecture_id: "lecture-01", passed_gates: 2, total_gates: 2 },
            { lecture_id: "lecture-02", passed_gates: 1, total_gates: 3 },
          ],
        },
      ],
    },
    loading: false,
    error: null,
    saveCalibration: vi.fn(),
    removePreference: vi.fn(),
    clearMemory: vi.fn(),
    refresh: vi.fn(),
  };
}

function json(value: unknown) {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
