import { vi } from "vitest";

import { localProfessorSession } from "../shell/appDefaults";
import { renderWithI18n } from "../test/renderWithI18n";
import type { CourseLectureStates, LectureState } from "./courseLectureStateTypes";
import { ProfessorCoursePage } from "./ProfessorCoursePage";
import type { ManagedCourseWorkspaceResult } from "../shared/types";

export const COURSE = "machine-learning";
const lectureRule = {
  audience: "tuebingen_enrolled",
  publication_mode: "on_lecture_date",
  publication_at: null,
} as const;

export const courseWorkspace: ManagedCourseWorkspaceResult = {
  course: { id: COURSE, title: "Machine Learning", professor: "Prof. Demo", term: "Winter 2026" },
  lectures: [
    {
      id: "lecture-01",
      number: "01",
      title: "Introduction",
      date: "2026-10-01",
      attendance: "unknown",
    },
    {
      id: "lecture-02",
      number: "02",
      title: "Gradient Descent",
      date: "2026-10-08",
      attendance: "unknown",
    },
  ],
  active_lecture_id: "lecture-01",
  accessSummary: {
    course_id: COURSE,
    default_rule: lectureRule,
    lectures: ["lecture-01", "lecture-02"].map((lecture_id) => ({
      lecture_id,
      rule_source: "course_default",
      rule: lectureRule,
      effective_publication_at: "2026-10-01T00:00:00Z",
      release_status: "released",
      content_ready: true,
    })),
  },
} as ManagedCourseWorkspaceResult;

export function lecture(id: string, patch: Partial<LectureState> = {}): LectureState {
  const number = id.slice(-2);
  return {
    lecture_id: id,
    number,
    title: `Lecture ${number}`,
    date: "2026-10-01",
    published: true,
    published_at: "2026-10-02T10:00:00Z",
    sources: "current",
    goals: "approved",
    draft: "published",
    draft_error: null,
    next_action: "none",
    ...patch,
  };
}

export function states(lectures: LectureState[]): CourseLectureStates {
  return { course_id: COURSE, routing: "confirmed", lectures };
}

export function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

type Handler = (init: RequestInit | undefined, url: string) => Response | Promise<Response>;

/** Routes "METHOD /path-suffix" to handlers; unknown requests fail the test loudly. */
export function mockApi(routes: Record<string, Handler>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    const path = new URL(url, "http://api.test").pathname;
    const match = Object.entries(routes).find(([key]) => {
      const [routeMethod, suffix] = key.split(" ");
      return routeMethod === method && path.endsWith(suffix);
    });
    if (!match) throw new Error(`Unexpected request: ${method} ${url}`);
    return match[1](init, url);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function calls(fetchMock: ReturnType<typeof mockApi>, method: string, suffix: string) {
  return fetchMock.mock.calls.filter(
    ([url, init]) => (init?.method ?? "GET") === method && String(url).endsWith(suffix),
  );
}

export function renderCoursePage(
  overrides: Partial<Parameters<typeof ProfessorCoursePage>[0]> = {},
) {
  const props = {
    workspace: courseWorkspace,
    session: localProfessorSession,
    onBack: vi.fn(),
    onCourseChanged: vi.fn(),
    onPreviewLecture: vi.fn(),
    onResumeCourse: vi.fn(),
    ...overrides,
  };
  renderWithI18n(<ProfessorCoursePage {...props} />);
  return props;
}
