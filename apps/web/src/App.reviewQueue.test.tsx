import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import App from "./App";
import { mockLoginFetch } from "./testFixtures";

it("opens a due review at its exact section and presents the bound transfer prompt", async () => {
  const baseFetch = mockLoginFetch({ published: true });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/review-queue") && init?.method !== "POST") return json(queue());
      if (url.endsWith("/review-queue/gates/lecture-03/losses-and-risks-p-1/open")) {
        return json(opening());
      }
      if (url.includes("/learner-state")) return json(emptyLessonState());
      return baseFetch(url, init);
    }),
  );
  const user = userEvent.setup();
  render(<App />);

  await logIn(user);
  await user.click(await screen.findByRole("button", { name: /open due review/i }));

  const prompt = await screen.findByText("Apply expected risk to an unfamiliar hospital case.");
  expect(prompt.closest(".message-list")).not.toBeNull();
  await waitFor(() => {
    expect(document.getElementById("losses-and-risks")).toHaveClass("is-focused");
    expect(document.getElementById("losses-and-risks-p-1")).toHaveClass("is-highlighted");
  });
  expect(within(screen.getByLabelText("Tutor drawer")).getByText("delayed transfer")).toBeVisible();
});

function queue() {
  return {
    course_id: "martius-ml",
    items: [
      {
        id: "gate:lecture-03:losses-and-risks-p-1",
        kind: "gate_review",
        course_id: "martius-ml",
        lecture_id: "lecture-03",
        lecture_title: "Bayesian Decision Theory",
        section_id: "losses-and-risks",
        section_title: "Losses, risks, and reject decisions",
        gate_id: "losses-and-risks-p-1",
        gate_revision: "revision-1",
        due_at: "2026-08-08T10:00:00+00:00",
      },
    ],
  };
}

function opening() {
  return {
    course_id: "martius-ml",
    lecture_id: "lecture-03",
    section_id: "losses-and-risks",
    gate_id: "losses-and-risks-p-1",
    gate_revision: "revision-1",
    prompt: "Apply expected risk to an unfamiliar hospital case.",
    stage: "due",
  };
}

function emptyLessonState() {
  return {
    course_id: "martius-ml",
    lecture_id: "lecture-03",
    gate_statuses: {},
    quiz_states: {},
    active_session_goal: null,
    pending_check: {
      gate_id: "losses-and-risks-p-1",
      gate_revision: "revision-1",
      prompt: "Apply expected risk to an unfamiliar hospital case.",
      assistance_level: "none",
      kind: "delayed_transfer",
    },
    due_gate_reviews: [],
  };
}

function json(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /continue with uni tübingen/i }));
}
