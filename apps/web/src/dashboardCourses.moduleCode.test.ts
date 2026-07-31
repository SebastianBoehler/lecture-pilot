import { describe, expect, it } from "vitest";

import { buildCourseGroups, findUniversityWorkspaceCourse } from "./dashboardCourses";
import type { Lecture, LoginSession, UniversityCourse } from "./types";

const workspaceCourse: UniversityCourse = {
  id: "softwarequalit-t-in-theorie-und-industrieller-praxis",
  title: "Softwarequalität in Theorie und Industrieller Praxis",
  professor: "professor-demo",
  term: "Sommer 2026",
};

const lecture: Lecture = {
  id: "lecture-01",
  number: "01",
  title: "Einführung und Kursüberblick",
  date: "2026-04-14",
  attendance: "unknown",
  contentReady: true,
};

const enrolledSession: LoginSession = {
  username: "student",
  term: "Sommer 2026",
  roles: ["student"],
  courses: [],
  university_courses: [
    {
      source: "alma",
      external_course_id: "unit:info4222",
      title: "INFO4222 Softwarequalität in Theorie und Industrieller Praxis",
      term: "Sommer 2026",
    },
  ],
};

describe("course-title module-code matching", () => {
  it("selects the same-term workspace when Alma adds a leading module code", () => {
    const selected = findUniversityWorkspaceCourse(
      [
        {
          id: "martius-ml",
          title: "Grundlagen des Maschinellen Lernens",
          professor: "Professor",
          term: "Sommer 2026",
        },
        workspaceCourse,
      ],
      enrolledSession.university_courses ?? [],
    );

    expect(selected).toEqual(workspaceCourse);
  });

  it("does not match an identically named workspace from another term", () => {
    const selected = findUniversityWorkspaceCourse(
      [{ ...workspaceCourse, term: "Winter 2025/26" }],
      enrolledSession.university_courses ?? [],
    );

    expect(selected).toBeUndefined();
  });

  it("prefers a newly bridged local workspace over an older database course", () => {
    const nlpWorkspace: UniversityCourse = {
      id: "info4193-natural-language-processing",
      title: "INFO4193 Natural Language Processing",
      professor: "Professor",
      term: "Sommer 2026",
    };
    const softwareQualityCourse = {
      ...workspaceCourse,
      id: "ff714e9b-abab-5c1b-9527-35d6831380bc",
    };

    const selected = findUniversityWorkspaceCourse(
      [softwareQualityCourse, nlpWorkspace],
      [
        ...(enrolledSession.university_courses ?? []),
        {
          source: "alma",
          external_course_id: "title:nlp",
          title: "INFO4193 Natural Language Processing",
          term: "Sommer 2026",
        },
      ],
      [softwareQualityCourse],
    );

    expect(selected).toEqual(nlpWorkspace);
  });

  it("renders the enrolled Alma course as the local tutor workspace", () => {
    const groups = buildCourseGroups(enrolledSession, workspaceCourse, [lecture], [lecture.id], {
      aiTutorAvailable: "AI tutor available",
      noTutor: "Not supported yet",
    });

    expect(groups).toHaveLength(1);
    expect(groups[0]).toMatchObject({
      course: workspaceCourse,
      tutorAvailable: true,
      statusLabel: "AI tutor available",
    });
    expect(groups[0].courseLectures).toEqual([lecture]);
  });
});
