import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import App from "./App";
import { localProfessorSession } from "./appDefaults";

afterEach(() => {
  window.localStorage.clear();
  window.history.replaceState({}, "", "/");
  vi.unstubAllGlobals();
});

it("opens a published lecture in a professor-owned student preview", async () => {
  const user = userEvent.setup();
  window.localStorage.setItem("lecturepilot.loginSession", JSON.stringify(localProfessorSession));
  const fetchMock = vi.fn(handleRequest);
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  await user.click(await screen.findByRole("button", { name: "Manage courses" }));
  expect(window.location.pathname).toBe("/professor/courses");
  await user.click(await screen.findByRole("button", { name: "Preview as student" }));

  expect(await screen.findByText("Student preview")).toBeInTheDocument();
  expect(window.location.pathname).toBe(
    "/professor/courses/demo-course/lectures/lecture-01/preview",
  );
  expect(screen.getByText(/stored only in your private preview/i)).toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Back to course management" }),
  ).not.toBeInTheDocument();

  const canvasCall = fetchMock.mock.calls.find(([url]) =>
    String(url).endsWith("/courses/demo-course/lectures/lecture-01/canvas"),
  );
  expect(new Headers(canvasCall?.[1]?.headers).get("X-LecturePilot-Learner-Preview")).toBe(
    "professor",
  );

  await user.click(screen.getByLabelText("Open tutor chat"));
  await user.type(screen.getByPlaceholderText(/ask about this lecture/i), "Test this concept.");
  await user.click(screen.getByRole("button", { name: /send message/i }));
  expect(await screen.findByText("Private preview answer.")).toBeInTheDocument();

  const turnCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/agent/turn/stream"));
  expect(new Headers(turnCall?.[1]?.headers).get("X-LecturePilot-Learner-Preview")).toBe(
    "professor",
  );
});

async function handleRequest(input: RequestInfo | URL, _init?: RequestInit) {
  const url = String(input);
  if (url.endsWith("/admin/courses")) {
    return json([
      {
        course: course(),
        lectures: [lecture()],
        active_lecture_id: "lecture-01",
        published_lecture_ids: ["lecture-01"],
        access_summary: accessSummary(true),
      },
    ]);
  }
  if (url.includes("/agent/turn/stream")) {
    return new Response(
      `${JSON.stringify({
        type: "result",
        result: {
          message: "Private preview answer.",
          canvas_commands: [],
          quality_gate: null,
          model: "test/model",
        },
      })}\n`,
      { status: 200 },
    );
  }
  if (url.includes("/courses/demo-course/lectures/lecture-01/canvas/publication")) {
    return json({ course_id: "demo-course", lecture_id: "lecture-01", published: true });
  }
  if (url.includes("/courses/demo-course/lectures/lecture-01/canvas")) {
    return json(canvas());
  }
  if (url.endsWith("/courses/demo-course/lectures")) {
    return json([{ lecture: lecture(), unlocked: true, attendance: "unknown" }]);
  }
  if (url.endsWith("/courses")) return json([course()]);
  if (url.includes("/canvas/publication")) return json({ published: false });
  return json([]);
}

function accessSummary(contentReady: boolean) {
  return {
    course_id: "demo-course",
    default_rule: {
      audience: "tuebingen_enrolled",
      publication_mode: "on_lecture_date",
      publication_at: null,
    },
    lectures: [
      {
        lecture_id: "lecture-01",
        rule_source: "course_default",
        rule: {
          audience: "tuebingen_enrolled",
          publication_mode: "on_lecture_date",
          publication_at: null,
        },
        effective_publication_at: "2026-05-05T22:00:00Z",
        release_status: "released",
        content_ready: contentReady,
      },
    ],
  };
}

function course() {
  return {
    id: "demo-course",
    title: "Machine Learning",
    professor: "Professor Demo",
    term: "Sommer 2026",
  };
}

function lecture() {
  return {
    id: "lecture-01",
    course_id: "demo-course",
    number: "01",
    title: "Introduction",
    date: "2026-06-01",
    attendance: "unknown",
  };
}

function canvas() {
  return {
    id: "demo-course-lecture-01",
    course_id: "demo-course",
    lecture_id: "lecture-01",
    title: "Introduction",
    source_kind: "generated",
    source_ref: "lecture-01.tex",
    sections: [
      {
        id: "introduction",
        title: "Introduction",
        blocks: [{ id: "intro-p", type: "paragraph", text: "Course content.", items: [] }],
      },
    ],
  };
}

function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
