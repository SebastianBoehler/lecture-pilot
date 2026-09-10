import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { I18nProvider } from "./i18n";
import { ProfessorPracticeHintEditor } from "./ProfessorPracticeHintEditor";
import { ProfessorHintEvidence } from "./ProfessorHintEvidence";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";

const target = practiceDesignFixture().targets[0];

function Editor() {
  const [current, setCurrent] = useState(target);
  return (
    <I18nProvider locale="en" setLocale={() => {}}>
      <ProfessorPracticeHintEditor disabled={false} target={current} onChange={setCurrent} />
      <output>{JSON.stringify(current.hint_ladder)}</output>
    </I18nProvider>
  );
}

describe("hint evidence bindings", () => {
  it("edits and clears rubric bindings without changing approved hint content", async () => {
    const user = userEvent.setup();
    render(<Editor />);
    const criterion = target.evidence_criteria[0];
    const checkbox = screen.getByRole("checkbox", { name: criterion.description });
    await user.click(checkbox);
    expect(checkbox).toBeChecked();
    expect(screen.getByRole("status")).toHaveTextContent(`"evidence_ids":["${criterion.id}"]`);
    expect(screen.getByRole("status")).toHaveTextContent(target.hint_ladder[0].content);
    await user.click(checkbox);
    expect(screen.getByRole("status")).toHaveTextContent('"evidence_ids":[]');
  });

  it("shows criterion descriptions in read-only review", () => {
    render(
      <I18nProvider locale="en" setLocale={() => {}}>
        <ProfessorHintEvidence
          target={target}
          hint={{ ...target.hint_ladder[0], evidence_ids: [target.evidence_criteria[0].id] }}
        />
      </I18nProvider>,
    );
    expect(screen.getByText(/Supports this learning evidence/)).toHaveTextContent(
      target.evidence_criteria[0].description,
    );
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });
});
