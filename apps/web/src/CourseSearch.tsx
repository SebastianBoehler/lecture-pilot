import { Search } from "lucide-react";
import { useEffect, useId, useState } from "react";

import { useI18n } from "./i18n";
import {
  MAX_SEARCH_LENGTH,
  MIN_SEARCH_LENGTH,
  searchCourse,
  type CourseSearchResult,
} from "./studyApi";
import type { Lecture, LoginSession, UniversityCourse } from "./types";

const SEARCH_DELAY_MS = 250;

type SearchState =
  | { status: "idle" }
  | { status: "loading"; query: string }
  | { status: "error"; query: string }
  | { status: "done"; query: string; result: CourseSearchResult };

export function CourseSearch({
  course,
  lectures,
  session,
  onOpenSection,
}: {
  course: UniversityCourse;
  lectures: Lecture[];
  session: LoginSession;
  onOpenSection: (lecture: Lecture, sectionId: string) => void;
}) {
  const { t } = useI18n();
  const resultsId = useId();
  const [query, setQuery] = useState("");
  const [state, setState] = useState<SearchState>({ status: "idle" });
  const trimmed = query.trim();
  const active = trimmed.length >= MIN_SEARCH_LENGTH;

  useEffect(() => {
    if (trimmed.length < MIN_SEARCH_LENGTH) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setState({ status: "loading", query: trimmed });
      searchCourse(course.id, trimmed, session, controller.signal)
        .then((result) => setState({ status: "done", query: trimmed, result }))
        .catch(() => {
          if (!controller.signal.aborted) setState({ status: "error", query: trimmed });
        });
    }, SEARCH_DELAY_MS);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [course.id, session, trimmed]);

  const current = active && state.status !== "idle" && state.query === trimmed ? state : null;
  const lecturesById = new Map(lectures.map((lecture) => [lecture.id, lecture]));

  return (
    <div className="course-search" role="search">
      <label className="course-search-field">
        <Search aria-hidden="true" size={15} />
        <span className="visually-hidden">{t("search.label", { course: course.title })}</span>
        <input
          aria-controls={active ? resultsId : undefined}
          maxLength={MAX_SEARCH_LENGTH}
          placeholder={t("search.placeholder")}
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      {active ? (
        <div aria-live="polite" className="course-search-results" id={resultsId}>
          {!current || current.status === "loading" ? (
            <p role="status">{t("search.loading")}</p>
          ) : null}
          {current?.status === "error" ? <p role="alert">{t("search.error")}</p> : null}
          {current?.status === "done" && !current.result.results.length ? (
            <p>{t("search.empty")}</p>
          ) : null}
          {current?.status === "done" && current.result.results.length ? (
            <ul aria-label={t("search.results")}>
              {current.result.results.map((hit) => {
                const lecture = lecturesById.get(hit.lecture_id);
                if (!lecture) return null;
                return (
                  <li key={`${hit.lecture_id}:${hit.section_id}`}>
                    <button
                      aria-label={t("search.openResult", {
                        lecture: hit.lecture_title,
                        section: hit.section_title,
                      })}
                      type="button"
                      onClick={() => onOpenSection(lecture, hit.section_id)}
                    >
                      <span className="course-search-hit-title">
                        <strong>{hit.section_title}</strong>
                        <small>
                          {lecture.number} · {hit.lecture_title}
                        </small>
                      </span>
                      {hit.snippet ? <span>{hit.snippet}</span> : null}
                    </button>
                  </li>
                );
              })}
            </ul>
          ) : null}
          {current?.status === "done" && current.result.truncated ? (
            <p>{t("search.truncated", { count: current.result.results.length })}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
