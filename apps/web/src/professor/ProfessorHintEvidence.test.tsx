import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { I18nProvider } from "../i18n/i18n";
import { ProfessorHintEvidence } from "./ProfessorHintEvidence";
import { practiceDesignFixture } from "./practiceDesignTestFixtures";

const target = practiceDesignFixture().targets[0];

describe("hint evidence bindings", () => {
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
