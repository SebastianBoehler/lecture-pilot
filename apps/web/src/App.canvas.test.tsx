import { act, fireEvent, render, screen, within } from "@testing-library/react";
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
    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));
    await user.click(screen.getByLabelText(/open tutor chat/i));
    await user.type(screen.getByPlaceholderText(/ask about this lecture/i), "Show me posterior.");
    await user.click(screen.getByRole("button", { name: /send message/i }));

    expect(await screen.findByText(/focus moved/i)).toBeInTheDocument();
    expect(document.querySelector(".phrase-highlight")?.textContent).toMatch(/posterior/i);
  });

  it("pulses an outline jump target and clears it after five seconds", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch());
    render(<App />);

    await logIn(user);
    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));
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

  it("shows section source references and the workspace file panel", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch());
    render(<App />);

    await logIn(user);
    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));

    const bayesSection = screen.getByRole("region", {
      name: /bayes formula and conditional probability/i,
    });
    const sourceFooter = within(bayesSection).getByText("Sources").closest("footer");
    expect(sourceFooter).toHaveTextContent(/Lecture03-eng\.tex/);
    expect(sourceFooter).toHaveTextContent(/frames 6, 7, 8, 9/);

    await user.click(screen.getByLabelText(/open file workspace/i));

    const filePanel = screen.getByRole("complementary", { name: /file workspace panel/i });
    expect(within(filePanel).getByRole("heading", { name: /workspace files/i })).toBeInTheDocument();
    expect(within(filePanel).getByText(/student canvas/i)).toBeInTheDocument();
    expect(within(filePanel).getAllByText(/Lecture03-eng\.tex/i).length).toBeGreaterThan(0);
    expect(within(filePanel).getByRole("button", { name: /Ch3\/spam-DALL-E\.jpg/i })).toBeInTheDocument();
  });

  it("opens source assets inside the workspace drawer instead of navigating away", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", mockLoginFetch());
    render(<App />);

    await logIn(user);
    await user.click(screen.getByRole("button", { name: /open lecture 03/i }));

    const decisionSection = screen.getByRole("region", { name: /decision making under uncertainty/i });
    await user.click(within(decisionSection).getByRole("button", { name: /Ch3\/spam-DALL-E\.jpg/i }));

    const filePanel = screen.getByRole("complementary", { name: /file workspace panel/i });
    expect(within(filePanel).getByRole("heading", { name: /workspace files/i })).toBeInTheDocument();
    expect(within(filePanel).getByRole("img", { name: /Ch3\/spam-DALL-E\.jpg/i })).toBeInTheDocument();
    expect(within(filePanel).getByRole("button", { name: /Ch3\/spam-DALL-E\.jpg/i })).toHaveAttribute(
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
