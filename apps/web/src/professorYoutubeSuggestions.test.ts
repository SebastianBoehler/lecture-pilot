import { describe, expect, it } from "vitest";

import { youtubeSuggestionQueries } from "./professorYoutubeSuggestions";
import type { CourseSetup } from "./professorBuilderState";
import type { Lecture } from "./types";

describe("professor YouTube suggestions", () => {
  it("scopes every suggested query to the selected lecture", () => {
    const queries = youtubeSuggestionQueries(setup(), lecture("lecture-06", "Decision Trees"));

    expect(queries).toHaveLength(3);
    expect(queries.every((query) => query.includes("Decision Trees"))).toBe(true);
    expect(queries.every((query) => !query.includes("Bayesian Decision Theory"))).toBe(true);
  });

  it("changes the search scope when another lecture is selected", () => {
    const first = youtubeSuggestionQueries(setup(), lecture("lecture-02", "Generalization"));
    const second = youtubeSuggestionQueries(setup(), lecture("lecture-10", "Deep Learning"));

    expect(first).not.toEqual(second);
    expect(first.every((query) => query.includes("Generalization"))).toBe(true);
    expect(second.every((query) => query.includes("Deep Learning"))).toBe(true);
  });
});

function setup(): CourseSetup {
  return {
    accessPolicy: "tuebingen_enrolled",
    courseTitle: "Grundlagen des Maschinellen Lernens",
    lectureTitle: "",
    lectureNumber: "",
    lectureCount: "",
    firstLectureDate: "2026-04-14",
    target: "full-course",
  };
}

function lecture(id: string, title: string): Lecture {
  return {
    attendance: "unknown",
    date: "2026-04-14",
    id,
    number: id.replace("lecture-", ""),
    title,
  };
}
