import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { openLecture03FromDashboard, soccerCanvasSection } from "./testLessonActions";
import { mockLoginAndTutorFetch } from "./testFixtures";

describe("Tutor canvas navigation", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    const elementPrototype = Element.prototype as { scrollIntoView?: unknown };
    delete elementPrototype.scrollIntoView;
  });

  it("scrolls to a newly created focused section instead of a stale highlight", async () => {
    const scrollTargets: string[] = [];
    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(function scrollIntoView(this: Element) {
        scrollTargets.push(this.id);
      }),
    });
    const tutorResponses = [
      {
        message: "Focus moved to Bayes evidence.",
        canvas_commands: [
          { type: "focus_section", section_id: "bayes-formula" },
          { type: "highlight_span", section_id: "bayes-formula", span_id: "bayes-formula-list" },
        ],
        quality_gate: gate(),
        artifacts: [],
        model: "local-guided-preview",
        created_at: "2026-06-05T20:00:00Z",
      },
      {
        message: "I added a detailed section.",
        canvas_commands: [
          {
            type: "append_section",
            section_id: "student-soccer-bayes-example",
            section: soccerCanvasSection(),
          },
          { type: "highlight_span", section_id: "bayes-formula", span_id: "bayes-formula-list" },
          { type: "focus_section", section_id: "student-soccer-bayes-example" },
        ],
        quality_gate: gate(),
        artifacts: [],
        model: "local-guided-preview",
        created_at: "2026-06-05T20:01:00Z",
      },
    ];
    const baseFetch = mockLoginAndTutorFetch();
    let tutorIndex = 0;
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      if (url.includes("/agent/turn/stream")) {
        return { ok: true, body: null };
      }
      if (url.includes("/agent/turn")) {
        const response = tutorResponses[tutorIndex] ?? tutorResponses.at(-1);
        tutorIndex += 1;
        return { ok: true, json: async () => response };
      }
      return baseFetch(url, init);
    }));
    const user = userEvent.setup();
    render(<App />);

    await logIn(user);
    await openLecture03FromDashboard(user);
    await user.click(screen.getByLabelText(/open tutor chat/i));
    await sendTutorMessage(user, "Show me the Bayes formula.");
    expect(await screen.findByText(/focus moved/i)).toBeInTheDocument();
    expect(scrollTargets.at(-1)).toBe("bayes-formula-list");

    scrollTargets.length = 0;
    await sendTutorMessage(user, "Create a detailed section.");
    expect(await screen.findByRole("heading", { name: /soccer scouting example/i })).toBeInTheDocument();
    expect(scrollTargets).not.toContain("bayes-formula-list");
    expect(scrollTargets.at(-1)).toBe("student-soccer-bayes-example");
  });
});

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /continue with uni tübingen/i }));
}

async function sendTutorMessage(user: ReturnType<typeof userEvent.setup>, message: string) {
  await user.type(screen.getByPlaceholderText(/ask about this lecture/i), message);
  await user.click(screen.getByRole("button", { name: /send message/i }));
}

function gate() {
  return {
    gate_id: "bayes-decision-check",
    status: "needs_evidence",
    reason: "The student needs to provide evidence.",
    next_prompt: "State the missing evidence.",
  };
}
