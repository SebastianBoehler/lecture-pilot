import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { CourseNameField } from "./CourseNameField";
import { I18nProvider } from "./i18n";

describe("course name field", () => {
  it("shows suggestion provenance and independent source availability", async () => {
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
          sourceStatuses={{ alma: "loading", ilias: "ready" }}
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
    expect(screen.getByText("Alma timetable: loading")).toBeInTheDocument();
    expect(screen.getByText("ILIAS memberships: available")).toBeInTheDocument();
    expect(screen.getByText("Alma catalogue: unavailable")).toBeInTheDocument();
  });
});
