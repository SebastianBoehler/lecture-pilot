import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorUsage } from "./ProfessorUsage";
import { localProfessorSession } from "./appDefaults";

describe("ProfessorUsage", () => {
  it("shows recorded provider usage separately from tutor safeguards", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(
            JSON.stringify({
              period_start: "2026-06-14",
              period_end: "2026-07-13",
              totals: {
                model_requests: 4,
                input_tokens: 12000,
                output_tokens: 3000,
                total_tokens: 15000,
                cached_input_tokens: 2000,
                reasoning_tokens: 500,
                tutor_turns: 2,
                images: 1,
              },
              workloads: [
                {
                  workload: "course_canvas",
                  model_requests: 3,
                  total_tokens: 13000,
                },
              ],
              courses: [
                {
                  course_id: "course-1",
                  course_title: "Machine Learning",
                  model_requests: 4,
                  total_tokens: 15000,
                  tutor_turns: 2,
                  images: 1,
                },
              ],
              daily: [
                {
                  date: "2026-07-13",
                  model_requests: 4,
                  total_tokens: 15000,
                  tutor_turns: 2,
                  images: 1,
                },
              ],
              limits: {
                turns_per_day: 200,
                reserved_tokens_per_day: 2000000,
                images_per_day: 20,
                concurrent_turns: 1,
                tokens_per_turn: 16000,
              },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        ),
      ),
    );

    render(
      <I18nProvider locale="en" setLocale={() => undefined}>
        <ProfessorUsage session={localProfessorSession} />
      </I18nProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Usage" })).toBeInTheDocument();
    expect(screen.getAllByText("15,000")).not.toHaveLength(0);
    expect(screen.getByText("Machine Learning")).toBeInTheDocument();
    expect(screen.getByText(/per learner and course/i)).toBeInTheDocument();
  });

  it("replaces the loading state with an API error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        Promise.resolve(
          new Response(JSON.stringify({ detail: "Usage is temporarily unavailable." }), {
            status: 503,
            headers: { "Content-Type": "application/json" },
          }),
        ),
      ),
    );

    render(
      <I18nProvider locale="en" setLocale={() => undefined}>
        <ProfessorUsage session={localProfessorSession} />
      </I18nProvider>,
    );

    expect(await screen.findByText("Usage is temporarily unavailable.")).toBeInTheDocument();
    expect(screen.queryByText("Loading usage...")).not.toBeInTheDocument();
  });
});
