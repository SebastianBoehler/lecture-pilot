import { useId, useMemo, useState } from "react";

import { useI18n } from "./i18n";
import type { CourseSuggestionSource, CourseTitleSuggestion } from "./professorCourseSuggestions";
import type { LoginSession } from "./types";

type SourceStatuses = NonNullable<LoginSession["university_course_source_statuses"]>;

export function CourseNameField({
  courseSearchFailed,
  courseSuggestions,
  onChange,
  sourceStatuses,
  value,
}: {
  courseSearchFailed: boolean;
  courseSuggestions: CourseTitleSuggestion[];
  onChange: (value: string) => void;
  sourceStatuses?: SourceStatuses;
  value: string;
}) {
  const { locale, t } = useI18n();
  const helpId = useId();
  const inputId = useId();
  const listId = useId();
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const visible = useMemo(() => {
    const query = value.trim().toLocaleLowerCase("de-DE");
    return courseSuggestions
      .filter((item) => !query || item.title.toLocaleLowerCase("de-DE").includes(query))
      .slice(0, 10);
  }, [courseSuggestions, value]);
  const copy = sourceCopy(locale);

  function choose(item: CourseTitleSuggestion) {
    onChange(item.title);
    setOpen(false);
  }

  return (
    <div className="course-name-field">
      <label htmlFor={inputId}>{t("builder.define.courseName")}</label>
      <input
        id={inputId}
        aria-activedescendant={open && visible.length ? `${listId}-${activeIndex}` : undefined}
        aria-autocomplete="list"
        aria-controls={listId}
        aria-describedby={helpId}
        aria-expanded={open && Boolean(visible.length)}
        autoComplete="off"
        role="combobox"
        value={value}
        onBlur={() => window.setTimeout(() => setOpen(false), 0)}
        onChange={(event) => {
          onChange(event.target.value);
          setActiveIndex(0);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setOpen(false);
          if (event.key === "ArrowDown" && visible.length) {
            event.preventDefault();
            setOpen(true);
            setActiveIndex((current) => (current + 1) % visible.length);
          }
          if (event.key === "ArrowUp" && visible.length) {
            event.preventDefault();
            setOpen(true);
            setActiveIndex((current) => (current - 1 + visible.length) % visible.length);
          }
          if (event.key === "Enter" && open && visible[activeIndex]) {
            event.preventDefault();
            choose(visible[activeIndex]);
          }
        }}
      />
      {open && visible.length ? (
        <ul className="course-suggestion-list" id={listId} role="listbox">
          {visible.map((item, index) => (
            <li
              aria-selected={index === activeIndex}
              id={`${listId}-${index}`}
              key={`${item.title}-${item.sources.join("-")}`}
              role="option"
            >
              <button
                type="button"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(item)}
              >
                <span>
                  <strong>{item.title}</strong>
                  {item.number || item.instructor ? (
                    <small>{[item.number, item.instructor].filter(Boolean).join(" · ")}</small>
                  ) : null}
                </span>
                <span className="course-suggestion-sources">
                  {item.sources.map((source) => (
                    <small key={source}>{copy.source[source]}</small>
                  ))}
                </span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <span className="course-source-statuses" aria-live="polite">
        {sourceStatuses ? (
          <>
            <small>
              {copy.alma}: {copy.status[sourceStatuses.alma ?? "loading"]}
            </small>
            <small>
              {copy.ilias}: {copy.status[sourceStatuses.ilias ?? "loading"]}
            </small>
          </>
        ) : null}
        <small>
          {copy.catalog}: {courseSearchFailed ? copy.status.error : copy.status.ready}
        </small>
      </span>
      <small className="course-name-match-note" id={helpId}>
        {t("builder.define.courseNameHelp")}
      </small>
    </div>
  );
}

function sourceCopy(locale: "de" | "en") {
  const source: Record<CourseSuggestionSource, string> =
    locale === "de"
      ? {
          alma_timetable: "ALMA Stundenplan",
          ilias_membership: "ILIAS Mitgliedschaft",
          alma_catalog: "ALMA Katalog",
        }
      : {
          alma_timetable: "Alma timetable",
          ilias_membership: "ILIAS membership",
          alma_catalog: "Alma catalogue",
        };
  return locale === "de"
    ? {
        alma: "ALMA Stundenplan",
        ilias: "ILIAS Mitgliedschaften",
        catalog: "ALMA Katalog",
        source,
        status: { loading: "wird geladen", ready: "verfügbar", error: "nicht verfügbar" },
      }
    : {
        alma: "Alma timetable",
        ilias: "ILIAS memberships",
        catalog: "Alma catalogue",
        source,
        status: { loading: "loading", ready: "available", error: "unavailable" },
      };
}
