import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ProfessorPerformanceDashboard } from "./ProfessorPerformanceDashboard";
import { localProfessorSession } from "./appDefaults";
import { renderWithI18n } from "./test/renderWithI18n";
import { course, lecture, noActivityCourse } from "./ProfessorCoursePerformance.testFixtures";

vi.mock("./professorApi", () => ({ listCourseWorkspaces: vi.fn() }));
import { listCourseWorkspaces } from "./professorApi";

describe("professor performance course discovery", () => {
  it("loads published managed courses without requiring a builder selection", async () => {
    vi.mocked(listCourseWorkspaces).mockResolvedValue([
      {
        course: course(),
        lectures: [lecture()],
        active_lecture_id: "lecture-01",
        publishedLectureIds: ["lecture-01"],
      },
      {
        course: { ...course(), id: "second", title: "Second course" },
        lectures: [lecture()],
        active_lecture_id: "lecture-01",
        publishedLectureIds: ["lecture-01"],
      },
      {
        course: { ...course(), id: "draft", title: "Draft only" },
        lectures: [lecture()],
        active_lecture_id: "lecture-01",
        publishedLectureIds: [],
      },
    ] as Awaited<ReturnType<typeof listCourseWorkspaces>>);
    const fetchMock = vi.fn(async (url: RequestInfo | URL) => {
      expect(String(url)).toContain("/analytics");
      return new Response(JSON.stringify(noActivityCourse()), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderWithI18n(<ProfessorPerformanceDashboard session={localProfessorSession} />);
    const select = await screen.findByRole("combobox", { name: "Course" });
    expect(screen.queryByRole("option", { name: "Draft only" })).not.toBeInTheDocument();
    await userEvent.setup().selectOptions(select, "second");
    expect(await screen.findByRole("heading", { name: "Course overview" })).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/second/"))).toBe(true);
  });
});
