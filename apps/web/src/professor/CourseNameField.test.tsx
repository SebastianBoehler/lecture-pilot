import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { CourseNameField } from "./CourseNameField";
import { I18nProvider } from "../i18n/i18n";

describe("course name field", () => {
  it("preserves suggestion provenance and shows catalogue errors", async () => {
    const user = userEvent.setup();
    render(
      <I18nProvider locale="en" setLocale={() => undefined}>
        <CourseNameField
          courseSearchFailed
          courseSuggestions={[
            {
              title: "Reliable Systems",
              sources: ["ilias_membership", "alma_catalog"],
            },
          ]}
          value="Reli"
          onChange={() => undefined}
        />
      </I18nProvider>,
    );

    await user.click(screen.getByRole("combobox"));

    expect(screen.getByRole("option", { name: /Reliable Systems/ })).toHaveTextContent(
      "ILIAS membership",
    );
    expect(screen.getByRole("option", { name: /Reliable Systems/ })).toHaveTextContent(
      "Alma catalogue",
    );
    expect(screen.getByText("Alma catalogue: unavailable")).toBeInTheDocument();
  });
});
