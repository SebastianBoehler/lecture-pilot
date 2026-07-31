import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ExamQuestionStep } from "./ExamQuestionStep";
import { I18nProvider } from "./i18n";

describe("ExamQuestionStep", () => {
  it("gives the question prompt its own prominent typography hook", () => {
    render(
      <I18nProvider locale="en" setLocale={vi.fn()}>
        <ExamQuestionStep
          answer={undefined}
          onAnswer={vi.fn()}
          question={{
            id: "question-1",
            kind: "multiple_choice",
            lecture_id: "lecture-01",
            lecture_title: "Introduction",
            options: ["First answer", "Second answer"],
            prompt: "What is the primary difference?",
            section_id: "section-1",
            section_title: "What is Machine Learning?",
          }}
        />
      </I18nProvider>,
    );

    expect(
      screen.getByText("What is the primary difference?").closest(".exam-question-prompt"),
    ).toBeInTheDocument();
    expect(screen.getByText("First answer")).not.toHaveClass("exam-question-prompt");
  });
});
