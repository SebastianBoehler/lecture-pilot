import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import App from "./App";
import { localProfessorSession } from "./appDefaults";

afterEach(() => {
  window.history.replaceState({}, "", "/");
});

it("loads the correct course draft without enabling unpublished tutor turns", async () => {
  window.localStorage.setItem("lecturepilot.loginSession", JSON.stringify(localProfessorSession));
  window.history.replaceState(
    {},
    "",
    "/?preview=draft&courseId=security-course&lectureId=lecture-01&lectureNumber=01&lectureTitle=Security",
  );
  const fetchMock = vi.fn(async (url: string, _init?: RequestInit) => {
    if (url.includes("/admin/courses/security-course/lectures/lecture-01/canvas/draft")) {
      return jsonResponse(draftCanvas());
    }
    if (url.includes("/agent/turn/stream")) {
      return new Response(
        `${JSON.stringify({
          type: "result",
          result: {
            message: "Scoped answer.",
            canvas_commands: [],
            quality_gate: null,
            model: "gemini/gemini-3.1-flash-lite",
          },
        })}\n`,
        { status: 200 },
      );
    }
    if (url.includes("/canvas/publication")) {
      return jsonResponse({ published: false });
    }
    if (url.endsWith("/courses/security-course/lectures")) {
      return jsonResponse([
        {
          id: "lecture-01",
          title: "Security",
          date: "Draft",
        },
      ]);
    }
    if (url.endsWith("/courses")) {
      return jsonResponse(localProfessorSession.courses);
    }
    return jsonResponse([]);
  });
  vi.stubGlobal("fetch", fetchMock);

  render(<App />);

  expect(
    await screen.findByRole("heading", { name: "Scoped draft" }, { timeout: 3_000 }),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/Tutor conversations and assessed attempts are available after publication/),
  ).toBeInTheDocument();
  expect(screen.queryByPlaceholderText(/ask about this lecture/i)).not.toBeInTheDocument();
  expect(fetchMock.mock.calls.some(([url]) => String(url).includes("/agent/turn/stream"))).toBe(
    false,
  );
});

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function draftCanvas() {
  return {
    id: "security-course-lecture-01",
    course_id: "security-course",
    lecture_id: "lecture-01",
    title: "Scoped draft",
    source_kind: "generated",
    source_ref: "Lecture01.md",
    sections: [
      {
        id: "scoped-section",
        title: "Scoped section",
        blocks: [{ id: "scoped-p", type: "paragraph", text: "Only this course.", items: [] }],
      },
    ],
  };
}
