import { useId } from "react";

import { formatAccessDate } from "./courseAccessStatus";
import { useI18n } from "./i18n";
import type {
  CourseAccessPolicy,
  CourseAccessRule,
  LecturePublicationMode,
} from "./courseAccessTypes";

export function CourseAccessFields({
  disabled,
  kind,
  lectureDate,
  rule,
  onChange,
}: {
  disabled: boolean;
  kind: "course" | "lecture";
  lectureDate: string;
  rule: CourseAccessRule;
  onChange: (rule: CourseAccessRule) => void;
}) {
  const { locale, t } = useI18n();
  const audienceName = useId();
  const releaseName = useId();
  const privateAudience = rule.audience === "instructors_only";
  const lectureDateLabel = formatLectureDate(lectureDate, locale);
  const audiences = [
    [
      "instructors_only",
      t("courseAccess.audience.instructors"),
      t("courseAccess.audience.instructorsHelp"),
    ],
    [
      "tuebingen_enrolled",
      t("courseAccess.audience.course"),
      t("courseAccess.audience.courseHelp"),
    ],
    [
      "platform_authenticated",
      t("courseAccess.audience.university"),
      t("courseAccess.audience.universityHelp"),
    ],
  ] as const;
  const releaseModes: Array<[LecturePublicationMode, string, string]> = [
    ["hidden", t("courseAccess.release.hidden"), t("courseAccess.release.hiddenHelp")],
    [
      "on_lecture_date",
      t("courseAccess.release.lectureDate"),
      kind === "course"
        ? t("courseAccess.release.lectureDateDefaultHelp")
        : t("courseAccess.release.lectureDateHelp", { date: lectureDateLabel }),
    ],
    ...(kind === "lecture"
      ? ([
          ["custom", t("courseAccess.release.custom"), t("courseAccess.release.customHelp")],
          ["published_now", t("courseAccess.release.now"), t("courseAccess.release.nowHelp")],
        ] as Array<[LecturePublicationMode, string, string]>)
      : []),
  ];

  return (
    <>
      <fieldset className="course-access-options" disabled={disabled}>
        <legend>{t("courseAccess.audience.legend")}</legend>
        {audiences.map(([value, label, help]) => (
          <label className="course-access-option" key={value}>
            <input
              checked={rule.audience === value}
              name={audienceName}
              type="radio"
              value={value}
              onChange={() =>
                onChange({
                  ...rule,
                  audience: value as CourseAccessPolicy,
                })
              }
            />
            <span>
              <strong>{label}</strong>
              <small>{help}</small>
            </span>
          </label>
        ))}
      </fieldset>

      <fieldset className="course-access-options" disabled={disabled || privateAudience}>
        <legend>{t("courseAccess.release.legend")}</legend>
        {privateAudience ? (
          <p className="course-access-field-note">{t("courseAccess.release.privateHelp")}</p>
        ) : null}
        {releaseModes.map(([value, label, help]) => (
          <label className="course-access-option" key={value}>
            <input
              checked={rule.publication_mode === value}
              name={releaseName}
              type="radio"
              value={value}
              onChange={() =>
                onChange({
                  ...rule,
                  publication_mode: value,
                  publication_at: value === "custom" ? rule.publication_at : null,
                })
              }
            />
            <span>
              <strong>{label}</strong>
              <small>{help}</small>
            </span>
          </label>
        ))}
      </fieldset>
    </>
  );
}

function formatLectureDate(value: string, locale: string) {
  const date = new Date(`${value}T12:00:00`);
  return Number.isNaN(date.getTime()) ? value : formatAccessDate(date, locale, false);
}
