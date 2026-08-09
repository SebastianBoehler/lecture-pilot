import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import { Dashboard } from "./Dashboard";
import { I18nProvider } from "./i18n";
import type { GateReviewOpening } from "./reviewQueueTypes";
import { renderWithI18n } from "./test/renderWithI18n";
import type { Lecture, LoginSession, UniversityCourse } from "./types";

afterEach(() => vi.unstubAllGlobals());

it("opens the explicitly validated due gate target", async () => {
  const user = userEvent.setup();
  const onOpen = vi.fn();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/open") && init?.method === "POST") {
      return json({
        course_id: course.id,
        lecture_id: "lecture-02",
        section_id: "risk",
        gate_id: "risk-check",
        gate_revision: "revision-1",
        prompt: "Apply risk to an unfamiliar hospital case.",
        stage: "due",
      });
    }
    return json(queue("student-a", "gate_review"));
  });
  vi.stubGlobal("fetch", fetchMock);
  renderDashboard(learner("student-a"), onOpen);

  await user.click(await screen.findByRole("button", { name: /open due review/i }));

  await waitFor(() =>
    expect(onOpen).toHaveBeenCalledWith(
      lectures[1],
      expect.objectContaining({
        gate_id: "risk-check",
        prompt: "Apply risk to an unfamiliar hospital case.",
        section_id: "risk",
      }),
    ),
  );
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining("/review-queue/gates/lecture-02/risk-check/open"),
    expect.objectContaining({ method: "POST" }),
  );
});

it("ignores a late queue response from the previous learner identity", async () => {
  let resolveA: ((response: Response) => void) | undefined;
  vi.stubGlobal(
    "fetch",
    vi.fn((_input: RequestInfo | URL, init?: RequestInit) => {
      const user = new Headers(init?.headers).get("X-User-Id");
      if (user === "student-a") {
        return new Promise<Response>((resolve) => {
          resolveA = resolve;
        });
      }
      return Promise.resolve(json(queue("student-b", "readiness_repair")));
    }),
  );
  const onOpen = vi.fn();
  const rendered = renderDashboard(learner("student-a"), onOpen);

  rendered.rerender(
    <I18nProvider locale="en" setLocale={() => undefined}>
      <Dashboard
        lectures={lectures}
        publishedLectureIds={lectures.map((lecture) => lecture.id)}
        session={learner("student-b")}
        workspaceCourse={course}
        onOpen={onOpen}
        onSetAttendance={vi.fn()}
      />
    </I18nProvider>,
  );

  expect(await screen.findByText("Student B repair")).toBeInTheDocument();
  await act(async () => resolveA?.(json(queue("student-a", "gate_review"))));
  expect(screen.getByText("Student B repair")).toBeInTheDocument();
  expect(screen.queryByText("Risk transfer")).not.toBeInTheDocument();
});

const course: UniversityCourse = {
  id: "review-course",
  title: "Review course",
  professor: "Professor",
  term: "2026",
};

const lectures: Lecture[] = [
  {
    id: "lecture-01",
    number: "01",
    title: "Foundations",
    date: "2026-04-01",
    attendance: "absent",
  },
  {
    id: "lecture-02",
    number: "02",
    title: "Risk",
    date: "2026-04-08",
    attendance: "present",
  },
];

function learner(username: string): LoginSession {
  return {
    username,
    tenant_id: "tenant-tuebingen",
    term: "2026",
    roles: ["student"],
    courses: [course],
  };
}

function renderDashboard(
  session: LoginSession,
  onOpen: (lecture: Lecture, review?: GateReviewOpening) => void,
) {
  return renderWithI18n(
    <Dashboard
      lectures={lectures}
      publishedLectureIds={lectures.map((lecture) => lecture.id)}
      session={session}
      workspaceCourse={course}
      onOpen={onOpen}
      onSetAttendance={vi.fn()}
    />,
  );
}

function queue(user: string, kind: "gate_review" | "readiness_repair") {
  return {
    course_id: course.id,
    items:
      kind === "gate_review"
        ? [
            {
              id: "gate:lecture-02:risk-check",
              kind,
              course_id: course.id,
              lecture_id: "lecture-02",
              lecture_title: "Risk",
              section_id: "risk",
              section_title: "Risk transfer",
              gate_id: "risk-check",
              gate_revision: "revision-1",
              due_at: "2026-08-08T10:00:00+00:00",
            },
          ]
        : [
            {
              id: `readiness:${user}`,
              kind,
              course_id: course.id,
              lecture_id: "lecture-01",
              lecture_title: "Foundations",
              section_id: "intro",
              section_title: "Student B repair",
              task_id: user,
              next_action: "Revisit the evidence.",
            },
          ],
  };
}

function json(value: unknown) {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
