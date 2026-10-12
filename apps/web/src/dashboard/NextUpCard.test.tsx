import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { NextUpCard } from "./NextUpCard";
import type { GateReviewQueueItem, ReadinessReviewQueueItem } from "./reviewQueueTypes";
import { renderWithI18n } from "../test/renderWithI18n";
import type { Lecture, UniversityCourse } from "../shared/types";

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

const course: UniversityCourse = {
  access_policy: "tuebingen_enrolled",
  id: "software-quality",
  title: "Softwarequalität in Theorie und Industrieller Praxis",
  professor: "University of Tübingen",
  term: "Sommer 2026",
};

describe("NextUpCard", () => {
  it("prioritizes an unpassed missed lecture and opens it", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    renderWithI18n(
      <NextUpCard
        course={course}
        lectures={candidateLectures}
        passedLectureIds={["lecture-01"]}
        onOpen={onOpen}
      />,
    );

    expect(screen.getByRole("heading", { name: "Next up" })).toBeInTheDocument();
    expect(screen.getByText(course.title)).toBeInTheDocument();
    expect(screen.getByText("02 · Generalization")).toBeInTheDocument();
    expect(screen.getByText(/missed this lecture/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Reviews" })).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: `Start recommended lecture 02 in ${course.title}` }),
    );
    expect(onOpen).toHaveBeenCalledWith(candidateLectures[1]);
  });

  it("puts a due gate review first and lists the remaining work below it", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    const onOpenGateReview = vi.fn();
    renderWithI18n(
      <NextUpCard
        course={course}
        lectures={candidateLectures}
        passedLectureIds={[]}
        reviewQueue={{
          course_id: course.id,
          items: [gateItem("gate:a", "Risk transfer"), readinessItem()],
          upcoming: [gateItem("gate:c", "Planned bounds")],
          completed: [
            {
              id: "done",
              course_id: course.id,
              lecture_id: "lecture-01",
              section_title: "Done",
              completed_at: "2026-08-01T10:00:00+00:00",
            },
          ],
        }}
        onOpen={onOpen}
        onOpenGateReview={onOpenGateReview}
      />,
    );

    expect(screen.getByText(/delayed transfer check is due/i)).toBeInTheDocument();
    const reviews = screen.getByRole("list");
    expect(within(reviews).queryByText("Risk transfer")).not.toBeInTheDocument();
    expect(within(reviews).getByText("Bounds")).toBeVisible();
    expect(within(reviews).getByText("Planned bounds")).toBeVisible();
    expect(screen.getByText("1 completed this week")).toBeVisible();
    expect(screen.getByRole("button", { name: /download calendar file/i })).toBeVisible();

    const primary = screen.getAllByRole("button", { name: /open due review/i })[0];
    await user.click(primary);
    expect(onOpenGateReview).toHaveBeenCalledWith(expect.objectContaining({ id: "gate:a" }));
    await user.click(within(reviews).getByRole("button", { name: /open readiness repair/i }));
    expect(onOpen).toHaveBeenCalledWith(candidateLectures[1]);
    await user.click(within(reviews).getByRole("button", { name: /^open lecture$/i }));
    expect(onOpen).toHaveBeenLastCalledWith(candidateLectures[2]);
  });

  it("shows a readiness task's evidence-driven next action before attendance continuation", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    renderWithI18n(
      <NextUpCard
        course={course}
        lectures={candidateLectures}
        passedLectureIds={[]}
        reviewQueue={{ course_id: course.id, upcoming: [], items: [readinessItem()] }}
        onOpen={onOpen}
      />,
    );

    expect(screen.getByText("Revisit the generalization bound.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /open readiness repair/i }));
    expect(onOpen).toHaveBeenCalledWith(candidateLectures[1]);
  });

  it("uses German messages and date formatting", () => {
    renderWithI18n(
      <NextUpCard
        course={course}
        lectures={candidateLectures}
        passedLectureIds={[]}
        reviewQueue={{ course_id: course.id, items: [], upcoming: [gateItem("gate:c", "Plan")] }}
        onOpen={vi.fn()}
      />,
      { locale: "de" },
    );

    expect(screen.getByRole("heading", { name: "Als Nächstes" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Wiederholungen" })).toBeVisible();
    expect(screen.getByText(/Sa\., 8\. Aug\./)).toBeVisible();
  });
});

function gateItem(id: string, sectionTitle: string): GateReviewQueueItem {
  return {
    id,
    kind: "gate_review",
    course_id: course.id,
    lecture_id: "lecture-03",
    lecture_title: "Bayes",
    section_id: "risk",
    section_title: sectionTitle,
    gate_id: id,
    gate_revision: "revision-1",
    due_at: "2026-08-08T10:00:00+00:00",
  };
}

function readinessItem(): ReadinessReviewQueueItem {
  return {
    id: "readiness:repair-risk",
    kind: "readiness_repair",
    course_id: course.id,
    lecture_id: "lecture-02",
    lecture_title: "Generalization",
    section_id: "bounds",
    section_title: "Bounds",
    task_id: "repair-risk",
    next_action: "Revisit the generalization bound.",
  };
}
