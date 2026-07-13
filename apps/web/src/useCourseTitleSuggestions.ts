import { useEffect, useMemo, useState } from "react";

import { searchAlmaCourseTitles } from "./professorApi";
import { mergeCourseTitles } from "./professorCourseSuggestions";
import type { LoginSession } from "./types";

export const COURSE_SEARCH_DEBOUNCE_MS = 400;

export function useCourseTitleSuggestions({
  enabled,
  personalTitles,
  query,
  session,
}: {
  enabled: boolean;
  personalTitles: string[];
  query: string;
  session: LoginSession;
}) {
  const [almaTitles, setAlmaTitles] = useState<string[]>([]);
  const [searchFailed, setSearchFailed] = useState(false);
  const hasExactPersonalTitle = personalTitles.some(
    (title) => title.localeCompare(query.trim(), "de-DE", { sensitivity: "base" }) === 0,
  );

  useEffect(() => {
    const normalizedQuery = query.trim();
    if (!enabled || normalizedQuery.length < 3 || hasExactPersonalTitle) {
      setAlmaTitles([]);
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
        setAlmaTitles(suggestions.map((item) => item.title));
      } catch (error) {
        if (!active || (error instanceof DOMException && error.name === "AbortError")) return;
        setAlmaTitles([]);
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
      () => mergeCourseTitles(personalTitles, almaTitles),
      [almaTitles, personalTitles],
    ),
    courseSearchFailed: searchFailed,
  };
}
