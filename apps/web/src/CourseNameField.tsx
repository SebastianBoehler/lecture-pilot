import { useId } from "react";

import { useI18n } from "./i18n";

export function CourseNameField({
  courseSuggestions,
  onChange,
  value,
}: {
  courseSuggestions: string[];
  onChange: (value: string) => void;
  value: string;
}) {
  const { t } = useI18n();
  const helpId = useId();

  return (
    <>
      {courseSuggestions.length ? (
        <label>
          {t("builder.define.universityCourse")}
          <select
            value={courseSuggestions.includes(value) ? value : ""}
            onChange={(event) => {
              if (event.target.value) onChange(event.target.value);
            }}
          >
            <option value="">{t("builder.define.universityCoursePlaceholder")}</option>
            {courseSuggestions.map((title) => (
              <option key={title} value={title}>
                {title}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <label>
        {t("builder.define.courseName")}
        <input
          aria-describedby={helpId}
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
        <small className="course-name-match-note" id={helpId}>
          {t("builder.define.courseNameHelp")}
        </small>
      </label>
    </>
  );
}
