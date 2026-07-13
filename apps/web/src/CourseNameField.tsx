import { useId } from "react";

import { useI18n } from "./i18n";

export function CourseNameField({
  courseSearchFailed,
  courseSuggestions,
  onChange,
  value,
}: {
  courseSearchFailed: boolean;
  courseSuggestions: string[];
  onChange: (value: string) => void;
  value: string;
}) {
  const { t } = useI18n();
  const helpId = useId();
  const suggestionsId = useId();
  const searchErrorId = useId();

  return (
    <label>
      {t("builder.define.courseName")}
      <input
        aria-describedby={`${helpId}${courseSearchFailed ? ` ${searchErrorId}` : ""}`}
        autoComplete="off"
        list={suggestionsId}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <datalist id={suggestionsId}>
        {courseSuggestions.map((title) => (
          <option key={title} value={title} />
        ))}
      </datalist>
      <small className="course-name-match-note" id={helpId}>
        {t("builder.define.courseNameHelp")}
      </small>
      {courseSearchFailed ? (
        <small className="form-error" id={searchErrorId}>
          {t("builder.define.courseSearchError")}
        </small>
      ) : null}
    </label>
  );
}
