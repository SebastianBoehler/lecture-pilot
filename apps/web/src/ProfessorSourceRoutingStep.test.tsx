import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorSourceRoutingStep } from "./ProfessorSourceRoutingStep";
import type { CourseSourceRoutingManifest } from "./types";

const routing: CourseSourceRoutingManifest = {
  confirmed: false,
  course_id: "nlp",
  source_revision: "a".repeat(64),
  routes: [
    {
      kind: "pdf",
      lecture_id: "lecture-03",
      path: "Lecture03.pdf",
      role: "lecture",
      sha256: "b".repeat(64),
    },
    {
      kind: "markdown",
      lecture_id: null,
      path: "build/cache.json",
      role: "excluded",
      sha256: "c".repeat(64),
    },
  ],
};

describe("ProfessorSourceRoutingStep", () => {
  it("makes every source route reviewable before confirmation", async () => {
    const user = userEvent.setup();
    const onRouteChange = vi.fn();
    const onConfirm = vi.fn();
    render(
      <I18nProvider locale="en" setLocale={() => undefined}>
        <ProfessorSourceRoutingStep
          isSaving={false}
          lectures={[
            { date: "2026-05-01", number: "03", title: "Language Models" },
            { date: "2026-05-08", number: "04", title: "Machine Translation" },
          ]}
          routing={routing}
          onConfirm={onConfirm}
          onRouteChange={onRouteChange}
        />
      </I18nProvider>,
    );

    expect(screen.getByRole("heading", { name: /review source assignments/i })).toBeInTheDocument();
    expect(screen.getByText(/agent proposed a destination for every file/i)).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "File" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Use in" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Lecture" })).toBeInTheDocument();
    expect(screen.getByText("cache.json")).toHaveClass("source-routing-name");
    expect(screen.getByText("build/")).toHaveClass("source-routing-directory");
    expect(screen.getByLabelText(/route build\/cache\.json/i)).toHaveValue("excluded");
    expect(screen.getByText(/sent only to the selected lecture/i)).toBeInTheDocument();
    expect(screen.getByText(/sent to every lecture/i)).toBeInTheDocument();
    expect(screen.getByText(/never sent to canvas generation/i)).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /reference only/i })).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/route build\/cache\.json/i), "lecture");
    expect(onRouteChange).toHaveBeenCalledWith("build/cache.json", "lecture", "lecture-03");

    await user.click(screen.getByRole("button", { name: /confirm assignments/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
