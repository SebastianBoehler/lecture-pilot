import { useEffect, useMemo, useState } from "react";

import { searchAlmaCourseTitles } from "./professorApi";
import {
  mergeCourseSuggestions,
  personalCourseSuggestions,
  type CourseTitleSuggestion,
} from "./professorCourseSuggestions";
import type { LoginSession } from "./types";
import type { UniversityEnrollmentCourse } from "./universityCourseTypes";

export const COURSE_SEARCH_DEBOUNCE_MS = 400;

export function useCourseTitleSuggestions({
  enabled,
  personalCourses,
  query,
  session,
}: {
  enabled: boolean;
  personalCourses: UniversityEnrollmentCourse[];
  query: string;
  session: LoginSession;
}) {
  const [catalogSuggestions, setCatalogSuggestions] = useState<CourseTitleSuggestion[]>([]);
  const [searchFailed, setSearchFailed] = useState(false);
  const personalSuggestions = useMemo(
    () => personalCourseSuggestions(personalCourses, session.term),
    [personalCourses, session.term],
  );
  const hasExactPersonalTitle = personalSuggestions.some(
    (item) => item.title.localeCompare(query.trim(), "de-DE", { sensitivity: "base" }) === 0,
  );

  useEffect(() => {
    const normalizedQuery = query.trim();
    if (!enabled || normalizedQuery.length < 3 || hasExactPersonalTitle) {
      setCatalogSuggestions([]);
      setSearchFailed(false);
      return;
    }

    const controller = new AbortController();
    let active = true;
    setSearchFailed(false);
    const timer = window.setTimeout(async () => {
      try {
        const suggestions = await searchAlmaCourseTitles(
          normalizedQuery,
          session.term,
          session,
          controller.signal,
        );
        if (!active) return;
        setCatalogSuggestions(
          suggestions.map((item) => ({
            title: item.title,
            sources: ["alma_catalog"],
            number: item.number,
            instructor: item.instructor,
          })),
        );
      } catch (error) {
        if (!active || (error instanceof DOMException && error.name === "AbortError")) return;
        setCatalogSuggestions([]);
        setSearchFailed(true);
      }
    }, COURSE_SEARCH_DEBOUNCE_MS);

    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [enabled, hasExactPersonalTitle, query, session]);

  return {
    courseSuggestions: useMemo(
      () => mergeCourseSuggestions([...personalSuggestions, ...catalogSuggestions]),
      [catalogSuggestions, personalSuggestions],
    ),
    courseSearchFailed: searchFailed,
  };
}
