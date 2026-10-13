import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { renderWithI18n } from "../test/renderWithI18n";
import { diffUnits, type SectionDiff } from "./canvasSectionDiff";
import { CanvasSectionDiffView } from "./CanvasSectionDiffView";

const changed = (title: string, before: string[], after: string[]): SectionDiff => ({
  kind: "changed",
  id: title,
  title,
  units: diffUnits(before, after),
});
const whole = (kind: "added" | "removed" | "unchanged", title: string, texts: string[]) => ({
  kind,
  id: title,
  title,
  units: texts.map((text) => ({ kind: kind === "unchanged" ? ("same" as const) : kind, text })),
});
const section = (title: string) => screen.getByRole("article", { name: title });

describe("CanvasSectionDiffView", () => {
  it("summarises the lecture and hides unchanged sections until asked", async () => {
    const user = userEvent.setup();
    renderWithI18n(
      <CanvasSectionDiffView
        sections={[
          whole("unchanged", "Intro", ["Hello."]),
          changed("Steps", ["Step one.", "Step two."], ["Step one.", "Step two, revised."]),
          whole("added", "New part", ["Fresh."]),
          whole("removed", "Old part", ["Gone."]),
        ]}
      />,
    );
    const summary = screen.getByRole("list", { name: "Summary of changes" });
    expect(
      within(summary)
        .getAllByRole("listitem")
        .map((item) => item.textContent),
    ).toEqual(["1 section changed", "1 added", "1 removed", "1 unchanged"]);
    expect(screen.queryByRole("article", { name: "Intro" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", { name: "Show unchanged sections" }));
    const intro = section("Intro");
    expect(within(intro).queryByText("Hello.")).not.toBeInTheDocument();
    await user.click(within(intro).getByRole("button", { name: "Show content" }));
    expect(await within(intro).findByText("Hello.")).toBeInTheDocument();
  });

  it("renders LaTeX and Markdown instead of their source", async () => {
    renderWithI18n(
      <CanvasSectionDiffView
        sections={[whole("added", "Gradient", ["Follow $\\nabla L(\\theta)$ with **care**."])]}
      />,
    );
    const added = section("Gradient");
    expect(await within(added).findByText("care")).toHaveProperty("tagName", "STRONG");
    expect(added.querySelector(".katex")).not.toBeNull();
    expect(added.textContent).not.toContain("$");
  });

  it("marks only the changed words of a lightly edited paragraph", async () => {
    renderWithI18n(
      <CanvasSectionDiffView
        sections={[
          changed(
            "Steps",
            ["Keep this.", "The step size is small here."],
            ["Keep this.", "The step size is tiny here."],
          ),
        ]}
      />,
    );
    const steps = section("Steps");
    expect((await within(steps).findByText("small")).closest("del")).not.toBeNull();
    expect((await within(steps).findByText("tiny")).closest("ins")).not.toBeNull();
    expect(within(steps).queryByRole("heading", { name: "Published" })).not.toBeInTheDocument();
  });

  it("shows a rewritten section side by side", async () => {
    renderWithI18n(
      <CanvasSectionDiffView
        sections={[
          changed(
            "Optimizers",
            ["Momentum keeps velocity.", "It smooths noisy updates."],
            ["Adam adapts the learning rate.", "Each weight gets its own scale."],
          ),
        ]}
      />,
    );
    const optimizers = section("Optimizers");
    expect(within(optimizers).getByText("Rewritten, shown side by side")).toBeInTheDocument();
    const before = within(optimizers).getByRole("region", { name: "Published" });
    const after = within(optimizers).getByRole("region", { name: "Draft" });
    expect(await within(before).findByText("Momentum keeps velocity.")).toBeInTheDocument();
    expect(await within(after).findByText("Adam adapts the learning rate.")).toBeInTheDocument();
    expect(within(after).queryByText("Momentum keeps velocity.")).not.toBeInTheDocument();
  });

  it("folds unchanged paragraphs and long new sections behind toggles", async () => {
    const user = userEvent.setup();
    const kept = ["A one.", "B two.", "C three.", "D four."];
    renderWithI18n(
      <CanvasSectionDiffView
        sections={[
          changed("Edited", [...kept, "Old end."], [...kept, "Old end, revised."]),
          whole("added", "Long", ["P1.", "P2.", "P3.", "P4.", "P5."]),
        ]}
      />,
    );
    const edited = section("Edited");
    const fold = within(edited).getByRole("button", { name: "3 unchanged paragraphs" });
    expect(fold).toHaveAttribute("aria-expanded", "false");
    await user.click(fold);
    expect(fold).toHaveAttribute("aria-expanded", "true");
    expect(await within(edited).findByText("A one.")).toBeInTheDocument();

    const long = section("Long");
    expect(within(long).getByText("5 paragraphs")).toBeInTheDocument();
    expect(within(long).queryByText("P5.")).not.toBeInTheDocument();
    await user.click(within(long).getByRole("button", { name: "Show all 5 paragraphs" }));
    expect(await within(long).findByText("P5.")).toBeInTheDocument();
  });

  it("says so when nothing changed", () => {
    renderWithI18n(<CanvasSectionDiffView sections={[whole("unchanged", "Intro", ["x"])]} />);
    expect(
      screen.getByText("The draft has the same content as the published version."),
    ).toBeInTheDocument();
  });
});
