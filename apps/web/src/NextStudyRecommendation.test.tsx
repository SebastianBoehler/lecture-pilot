import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { NextStudyRecommendation } from "./NextStudyRecommendation";
import { renderWithI18n } from "./test/renderWithI18n";
import type { Lecture } from "./types";

const candidateLectures: Lecture[] = [
  {
    id: "lecture-01",
    number: "01",
    title: "Foundations",
    date: "2026-04-01",
    attendance: "present",
  },
  {
    id: "lecture-02",
    number: "02",
    title: "Generalization",
    date: "2026-04-08",
    attendance: "absent",
  },
  { id: "lecture-03", number: "03", title: "Bayes", date: "2026-04-15", attendance: "unknown" },
];

describe("NextStudyRecommendation", () => {
  it("prioritizes an unpassed missed lecture and opens it", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    renderWithI18n(
      <NextStudyRecommendation
        lectures={candidateLectures}
        passedLectureIds={["lecture-01"]}
        onOpen={onOpen}
      />,
    );

    expect(screen.getByRole("heading", { name: /next study step/i })).toBeInTheDocument();
    expect(screen.getByText("Generalization")).toBeInTheDocument();
    expect(screen.getByText(/missed this lecture/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /start recommended lecture 02/i }));
    expect(onOpen).toHaveBeenCalledWith(candidateLectures[1]);
  });
});
