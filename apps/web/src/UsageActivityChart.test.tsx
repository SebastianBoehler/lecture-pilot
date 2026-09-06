import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import { UsageActivityChart } from "./UsageActivityChart";
import { renderWithI18n } from "./test/renderWithI18n";
import type { ProfessorUsageSummary } from "./usageTypes";

it("switches real daily measures and keeps the entire period accessible", async () => {
  const usage = {
    period_start: "2026-07-01",
    period_end: "2026-07-30",
    daily: [
      { date: "2026-07-01", model_requests: 8, total_tokens: 100, tutor_turns: 2, images: 0 },
    ],
  } as ProfessorUsageSummary;
  renderWithI18n(<UsageActivityChart usage={usage} />);
  expect(screen.getByRole("img", { name: /Model requests/ })).toBeInTheDocument();
  expect(document.querySelectorAll("svg rect")).toHaveLength(30);
  await userEvent
    .setup()
    .selectOptions(screen.getByRole("combobox", { name: "Measure" }), "tutor_turns");
  expect(screen.getByRole("img", { name: /Tutor requests/ })).toBeInTheDocument();
  await userEvent.setup().click(screen.getByText("View daily values"));
  expect(screen.getByRole("cell", { name: "2" })).toBeVisible();
  expect(screen.getByRole("rowheader", { name: "2026-07-30" })).toBeVisible();
});
