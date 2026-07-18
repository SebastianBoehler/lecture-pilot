import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  datetimeLocalValue,
  lectureAvailability,
  publicationAtFromLocal,
} from "./courseAccessStatus";
import { ProfessorLectureAccessStatus } from "./ProfessorLectureAccessStatus";
import { renderWithI18n } from "./test/renderWithI18n";

describe("course access status", () => {
  const now = new Date("2026-07-14T07:00:00Z");

  it("uses the later of an immediate request and the lecture date", () => {
    const result = lectureAvailability(
      { audience: "tuebingen_enrolled", publication_mode: "published_now", publication_at: null },
      "2026-07-18",
      true,
      now,
    );

    expect(result.state).toBe("scheduled");
    expect(result.availableAt?.toISOString()).toBe("2026-07-17T22:00:00.000Z");
  });

  it("round-trips custom times in the course timezone", () => {
    const publicationAt = publicationAtFromLocal("2026-07-18T09:00");

    expect(publicationAt).toBe("2026-07-18T07:00:00.000Z");
    expect(datetimeLocalValue(publicationAt)).toBe("2026-07-18T09:00");
  });

  it("shows audience, exact date, and relative countdown in one compact status", () => {
    renderWithI18n(
      <ProfessorLectureAccessStatus
        now={now}
        summary={{
          lecture_id: "lecture-01",
          rule_source: "lecture_override",
          rule: {
            audience: "tuebingen_enrolled",
            publication_mode: "custom",
            publication_at: "2026-07-18T07:00:00Z",
          },
          effective_publication_at: "2026-07-18T07:00:00Z",
          release_status: "scheduled",
          content_ready: true,
        }}
      />,
    );

    expect(screen.getByLabelText("Course participants")).toHaveTextContent("Course");
    expect(screen.getByText(/Available 18 Jul 2026, 09:00 · in 4 days/)).toBeInTheDocument();
  });
});
