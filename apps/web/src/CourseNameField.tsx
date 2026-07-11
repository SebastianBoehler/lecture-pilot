import { useId } from "react";

import { useI18n } from "./i18n";

export function CourseNameField({
  onChange,
  value,
}: {
  onChange: (value: string) => void;
  value: string;
}) {
  const { t } = useI18n();
  const helpId = useId();

  return (
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
  );
}
