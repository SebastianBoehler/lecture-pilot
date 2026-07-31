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
      path: "exam-protocols/README.md",
      role: "reference_only",
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

    expect(screen.getByRole("heading", { name: /review source routing/i })).toBeInTheDocument();
    expect(screen.getByText("exam-protocols/README.md")).toBeInTheDocument();
    expect(screen.getByLabelText(/route exam-protocols\/readme\.md/i)).toHaveValue(
      "reference_only",
    );
    expect(
      screen.getByText(/reference only files are kept out of generation/i),
    ).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/route exam-protocols\/readme\.md/i), "lecture");
    expect(onRouteChange).toHaveBeenCalledWith("exam-protocols/README.md", "lecture", "lecture-03");

    await user.click(screen.getByRole("button", { name: /confirm source routing/i }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
