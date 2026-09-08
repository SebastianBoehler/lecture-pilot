import { describe, expect, it, vi } from "vitest";
import { createWebMcpTools, type WebMcpState } from "./webMcpTools";
import { localDemoSession } from "./appDefaults";

function fixture() {
  const state: WebMcpState = {
    session: localDemoSession,
    theme: "light",
    locale: "en",
    busy: false,
    navigate: vi.fn(),
    openCourse: vi.fn(),
    setTheme: vi.fn(),
    setLocale: vi.fn(),
  };
  const lecture = {
    id: "lecture-01",
    title: "Introduction",
    number: "1",
    date: "2026-01-01",
    attendance: "unknown" as const,
    contentReady: true,
    unlocked: true,
    releaseStatus: "released" as const,
  };
  const dependencies = {
    getCourseLectures: vi.fn().mockResolvedValue([lecture]),
    getLearnerProfile: vi.fn().mockResolvedValue({
      courses: [
        {
          course_id: localDemoSession.courses[0].id,
          passed_lecture_ids: [lecture.id],
          memory: "PRIVATE",
        },
      ],
      global_notes: "PRIVATE",
    }),
    getLearnerLessonState: vi.fn().mockResolvedValue({
      publication_version: 3,
      gate_statuses: { intro: "passed" },
      pending_check: { prompt: "SECRET" },
      quiz_states: { answer: "SECRET" },
      goal_evidence: [
        {
          gate_id: "intro",
          gate_revision: "r1",
          supported: true,
          independent: false,
          delayed: false,
          missing_evidence: ["SECRET"],
        },
      ],
    }),
  };
  const tools = createWebMcpTools(() => state, dependencies);
  const call = (name: string, input = {}) =>
    tools.find((t) => t.name === `lecturepilot_${name}`)!.execute(input);
  return { state, dependencies, tools, call, lecture, course_id: localDemoSession.courses[0].id };
}

describe("student WebMCP boundary", () => {
  it("exposes only the navigation, display and read-only context allowlist", () => {
    expect(fixture().tools.map((t) => t.name)).toEqual([
      "lecturepilot_list_courses",
      "lecturepilot_get_course_context",
      "lecturepilot_get_learning_progress",
      "lecturepilot_open_course",
      "lecturepilot_open_lecture",
      "lecturepilot_get_display_settings",
      "lecturepilot_set_display_settings",
    ]);
  });
  it("projects progress without answers, tasks or memory", async () => {
    const f = fixture();
    const result = await f.call("get_learning_progress", {
      course_id: f.course_id,
      lecture_id: f.lecture.id,
    });
    expect(result).toMatchObject({
      publication_version: 3,
      gate_statuses: { intro: "passed" },
      evidence: [{ gate_id: "intro", independent: false }],
    });
    expect(JSON.stringify(result)).not.toMatch(/SECRET|PRIVATE|pending_check|quiz_states/);
  });
  it("rejects unauthorized courses and extra input before accessing the API", async () => {
    const f = fixture();
    await expect(f.call("open_course", { course_id: "other" })).rejects.toThrow(/authorized/);
    await expect(f.call("open_course", { course_id: f.course_id, answer: "yes" })).rejects.toThrow(
      /Unexpected/,
    );
    expect(f.dependencies.getCourseLectures).not.toHaveBeenCalled();
  });
  it("rejects hidden, scheduled, locked and unpublished lectures", async () => {
    for (const patch of [
      { releaseStatus: "hidden" },
      { releaseStatus: "scheduled" },
      { unlocked: false },
      { contentReady: false },
    ]) {
      const f = fixture();
      f.dependencies.getCourseLectures.mockResolvedValue([{ ...f.lecture, ...patch }]);
      await expect(
        f.call("open_lecture", { course_id: f.course_id, lecture_id: f.lecture.id }),
      ).rejects.toThrow(/available/);
      expect(f.state.navigate).not.toHaveBeenCalled();
    }
  });
  it("navigates to the learner route and changes only supported display values", async () => {
    const f = fixture();
    await f.call("open_lecture", { course_id: f.course_id, lecture_id: f.lecture.id });
    expect(f.state.navigate).toHaveBeenCalledWith(
      `/courses/${f.course_id}/lectures/${f.lecture.id}`,
    );
    await f.call("set_display_settings", { theme: "dark", language: "de" });
    expect(f.state.setTheme).toHaveBeenCalledWith("dark");
    expect(f.state.setLocale).toHaveBeenCalledWith("de");
    await expect(f.call("set_display_settings", { theme: "system" })).rejects.toThrow();
  });
  it("blocks navigation during learning interactions", async () => {
    const f = fixture();
    f.state.busy = true;
    await expect(f.call("open_course", { course_id: f.course_id })).rejects.toThrow(/student/);
    expect(f.state.openCourse).not.toHaveBeenCalled();
  });
  it("discards pending results after logout", async () => {
    const f = fixture();
    f.dependencies.getCourseLectures.mockImplementation(async () => {
      f.state.session = null;
      return [f.lecture];
    });
    await expect(
      f.call("open_lecture", { course_id: f.course_id, lecture_id: f.lecture.id }),
    ).rejects.toThrow(/session/);
    expect(f.state.navigate).not.toHaveBeenCalled();
  });
});
