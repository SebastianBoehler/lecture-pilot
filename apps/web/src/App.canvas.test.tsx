import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { mockLoginAndTutorFetch, mockLoginFetch } from "./testFixtures";

describe("LecturePilot canvas interactions", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("highlights tutor-selected phrases inside the focused canvas block", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      mockLoginAndTutorFetch({
        tutorResponse: {
          message: "Focus moved to posterior evidence.",
          canvas_commands: [
            { type: "focus_section", section_id: "bayes-formula" },
            {
              type: "highlight_span",
              section_id: "bayes-formula",
              span_id: "bayes-formula-list",
              highlight_text: "Posterior",
            },
          ],
          quality_gate: {
            gate_id: "bayes-decision-check",
            status: "needs_evidence",
            reason: "The student must connect posterior to risk.",
            next_prompt: "Explain how posterior supports the decision.",
          },
          artifacts: [],
          model: "local-guided-preview",
          created_at: "2026-06-05T20:00:00Z",
        },
      }),
    );
    render(<App />);

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));
    await user.click(screen.getByLabelText(/open tutor chat/i));
    await user.type(screen.getByPlaceholderText(/ask about this lecture/i), "Show me posterior.");
    await user.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByText(/focus moved/i)).toBeInTheDocument();
    expect(document.querySelector(".phrase-highlight")?.textContent).toMatch(/posterior/i);
    expect(document.getElementById("bayes-formula-list")).not.toHaveClass("is-highlighted");
  });

  it("submits retrieval quiz options as tutor turns", async () => {
    const user = userEvent.setup();
    const fetchMock = mockLoginAndTutorFetch();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));
    const correct = screen.getByRole("button", { name: /B Expected risk/i });
    await user.click(correct);

    expect(await screen.findByPlaceholderText(/ask about this lecture/i)).toBeInTheDocument();
    expect(await screen.findByText(/Retrieval quiz answer for "Retrieval check": B\. Expected risk/i))
      .toBeInTheDocument();

    const agentCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/agent/turn"));
    expect(agentCall).toBeDefined();
    const request = JSON.parse(String(agentCall?.[1]?.body));
    expect(request.message).toContain("Question: Which quantity should be minimized");
    expect(request.message).toContain("B. Expected risk");
    await waitFor(() => {
      const analyticsCall = fetchMock.mock.calls.find(([url]) => String(url).includes("/analytics/quiz-answer"));
      expect(analyticsCall).toBeDefined();
      expect(JSON.parse(String(analyticsCall?.[1]?.body))).toMatchObject({
        user_id: "student01",
        attendance: "absent",
        block_id: "losses-and-risks-quiz",
        option_index: 1,
      });
    });
    expect(correct).toHaveClass("is-correct");
  });

  it("renders prefab component quizzes inside the canvas", async () => {
    const user = userEvent.setup();
    const fetchMock = mockLoginAndTutorFetch();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));
    const componentAnswer = screen.getByRole("button", { name: /A The loss-sensitive threshold/i });
    await user.click(componentAnswer);

    expect(await screen.findByText(/Retrieval quiz answer for "Risk threshold component": A/i))
      .toBeInTheDocument();
    expect(componentAnswer).toHaveClass("is-correct");
  });

  it("pulses an outline jump target and clears it after five seconds", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    render(<App />);

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));
    await user.click(screen.getByLabelText(/open document outline/i));

    const outline = screen.getByRole("navigation", { name: /lesson document outline/i });
    const bayesGroup = within(outline).getByRole("group", {
      name: /bayes formula and conditional probability related items/i,
    });
    vi.useFakeTimers();
    await act(async () => {
      fireEvent.click(within(bayesGroup).getByRole("button", { name: /key ideas/i }));
    });

    const target = document.getElementById("bayes-formula-list");
    expect(target).toHaveClass("is-outline-pulsed");

    await act(async () => {
      vi.advanceTimersByTime(5000);
    });

    expect(target).not.toHaveClass("is-outline-pulsed");
  });

  it("shows a collapsible workspace file explorer", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    render(<App />);

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));

    const bayesSection = screen.getByRole("region", {
      name: /bayes formula and conditional probability/i,
    });
    const sourceFooter = within(bayesSection).getByText("Sources").closest("footer");
    expect(sourceFooter).toHaveTextContent(/Lecture03-eng\.tex/);
    expect(sourceFooter).toHaveTextContent(/frames 6, 7, 8, 9/);
    expect(within(bayesSection).getByRole("img", { name: /Ch3\/Venn_C-X_1\.pdf/i })).toBeInTheDocument();

    await user.click(screen.getByLabelText(/open file workspace/i));

    const filePanel = screen.getByRole("complementary", { name: /file workspace panel/i });
    expect(within(filePanel).getByRole("heading", { name: /workspace files/i })).toBeInTheDocument();
    expect(within(filePanel).queryByText(/section references/i)).not.toBeInTheDocument();

    const tree = within(filePanel).getByRole("tree", { name: /workspace file tree/i });
    expect(within(tree).getByRole("button", { name: /collapse \.lecturepilot/i })).toBeInTheDocument();
    expect(within(tree).getByRole("button", { name: /collapse local-course-materials/i })).toBeInTheDocument();
    expect(within(tree).getByRole("button", { name: /open index\.md/i })).toBeInTheDocument();
    expect(within(tree).getByRole("button", { name: /open Lecture03-eng\.tex/i })).toBeInTheDocument();
    expect(within(tree).getByRole("button", { name: /open Venn_C-X_1\.pdf/i })).toBeInTheDocument();
    expect(within(tree).getByRole("button", { name: /open spam-DALL-E\.jpg/i })).toBeInTheDocument();

    await user.click(within(tree).getByRole("button", { name: /collapse sections/i }));
    expect(within(tree).queryByRole("button", { name: /open 02-bayes-formula\.md/i })).not.toBeInTheDocument();

    await user.click(within(tree).getByRole("button", { name: /expand sections/i }));
    expect(within(tree).getByRole("button", { name: /open 02-bayes-formula\.md/i })).toBeInTheDocument();
  });

  it("opens inline source markers as traced source previews", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    render(<App />);

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));

    const bayesSection = screen.getByRole("region", {
      name: /bayes formula and conditional probability/i,
    });
    const inlineSourceMarkers = within(bayesSection).getAllByRole("button", {
      name: /open source 1 for bayes formula and conditional probability/i,
    });
    expect(inlineSourceMarkers).toHaveLength(1);
    expect(document.querySelector("#bayes-formula-math-1 .inline-source-marker")).toBeNull();
    await user.click(inlineSourceMarkers[0]);

    const filePanel = screen.getByRole("complementary", { name: /file workspace panel/i });
    const preview = within(filePanel).getByRole("region", { name: /selected file preview/i });
    expect(within(preview).getByText(/source file/i)).toBeInTheDocument();
    expect(within(preview).getByText(/trace target/i)).toBeInTheDocument();
    expect(within(preview).getByText(/frames 6, 7, 8, 9/i)).toBeInTheDocument();
    expect(within(filePanel).getByRole("button", { name: /open Lecture03-eng\.tex/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("groups consecutive formulas into a compact derivation block", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    render(<App />);

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));

    const lossesSection = screen.getByRole("region", {
      name: /losses, risks, and reject decisions/i,
    });
    const derivation = lossesSection.querySelector(".canvas-derivation");

    expect(derivation).not.toBeNull();
    expect(within(lossesSection).getByText("Derivation")).toBeInTheDocument();
    expect(derivation?.querySelectorAll(".canvas-math")).toHaveLength(3);
    expect(lossesSection.querySelector(".canvas-prose-run")).not.toBeNull();
  });

  it("renders approved YouTube videos as inline canvas artifacts", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    render(<App />);

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));

    const videoSection = screen.getByRole("region", { name: /professor selected videos/i });
    const frame = within(videoSection).getByTitle(/bayesian decision theory walkthrough/i);

    expect(frame).toHaveAttribute("src", "https://www.youtube-nocookie.com/embed/abc123abc12");
    expect(within(videoSection).getByText(/ML Course · 12:30/i)).toBeInTheDocument();

    await user.click(screen.getByLabelText(/open document outline/i));
    const outline = screen.getByRole("navigation", { name: /lesson document outline/i });
    expect(within(outline).getByRole("button", { name: /bayesian decision theory walkthrough/i })).toBeInTheDocument();
  });

  it("opens source assets inside the workspace drawer instead of navigating away", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch({ published: true }));
    render(<App />);

    await logIn(user);
    await user.click(await screen.findByRole("button", { name: /open lecture 03/i }));

    const decisionSection = screen.getByRole("region", { name: /decision making under uncertainty/i });
    await user.click(within(decisionSection).getByRole("button", { name: /Ch3\/spam-DALL-E\.jpg/i }));

    const filePanel = screen.getByRole("complementary", { name: /file workspace panel/i });
    expect(within(filePanel).getByRole("heading", { name: /workspace files/i })).toBeInTheDocument();
    expect(within(filePanel).getByRole("img", { name: /Ch3\/spam-DALL-E\.jpg/i })).toBeInTheDocument();
    expect(within(filePanel).getByRole("button", { name: /open spam-DALL-E\.jpg/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});

async function logIn(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/zdv username/i), "student01");
  await user.type(screen.getByLabelText(/^password$/i), "very-secret-password");
  await user.click(screen.getByRole("button", { name: /connect to tue api/i }));
}
