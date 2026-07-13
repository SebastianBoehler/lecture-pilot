import { CourseNameField } from "./CourseNameField";
import { useI18n } from "./i18n";
import type { CourseSetup } from "./professorBuilderState";
import { PendingStatus, StepHeader } from "./ProfessorCourseBuilderParts";

export function ProfessorCourseSetupStep({
  courseSearchFailed,
  courseSuggestions,
  courseReady,
  isCreating,
  isReady,
  onCreate,
  onSetupChange,
  setup,
}: {
  courseSearchFailed: boolean;
  courseSuggestions: string[];
  courseReady: boolean;
  isCreating: boolean;
  isReady: boolean;
  onCreate: () => void;
  onSetupChange: (setup: CourseSetup) => void;
  setup: CourseSetup;
}) {
  const { t } = useI18n();
  return (
    <section className="flow-card wide">
      <StepHeader number="01" title={t("builder.define.title")} done={courseReady} />
      <CourseNameField
        courseSearchFailed={courseSearchFailed}
        courseSuggestions={courseSuggestions}
        value={setup.courseTitle}
        onChange={(courseTitle) => onSetupChange({ ...setup, courseTitle })}
      />
      <label>
        {t("builder.define.visibility")}
        <select
          value={setup.accessPolicy}
          onChange={(event) =>
            onSetupChange({
              ...setup,
              accessPolicy: event.target.value as CourseSetup["accessPolicy"],
            })
          }
        >
          <option value="tuebingen_enrolled">{t("builder.define.visibility.enrolled")}</option>
          <option value="platform_authenticated">
            {t("builder.define.visibility.university")}
          </option>
          <option value="public">{t("builder.define.visibility.public")}</option>
        </select>
      </label>
      <div className="scope-toggle" role="group" aria-label={t("builder.define.scope")}>
        <button
          aria-pressed={setup.target === "single-lecture"}
          className={setup.target === "single-lecture" ? "is-active" : ""}
          type="button"
          onClick={() => onSetupChange({ ...setup, target: "single-lecture" })}
        >
          {t("builder.define.specificLecture")}
        </button>
        <button
          aria-pressed={setup.target === "full-course"}
          className={setup.target === "full-course" ? "is-active" : ""}
          type="button"
          onClick={() => onSetupChange({ ...setup, target: "full-course", lectureCount: "" })}
        >
          {t("builder.define.fullCourse")}
        </button>
      </div>
      {setup.target === "single-lecture" ? (
        <div className="flow-grid">
          <label>
            {t("builder.define.lectureNumber")}
            <input
              value={setup.lectureNumber}
              onChange={(event) => onSetupChange({ ...setup, lectureNumber: event.target.value })}
            />
          </label>
          <label>
            {t("builder.define.lectureTitle")}
            <input
              value={setup.lectureTitle}
              onChange={(event) => onSetupChange({ ...setup, lectureTitle: event.target.value })}
            />
          </label>
        </div>
      ) : (
        <div className="flow-grid course-scope-grid">
          <label>
            {t("builder.define.expectedLectures")}
            <input
              min="1"
              placeholder={t("builder.define.inferFromMaterials")}
              type="number"
              value={setup.lectureCount}
              onChange={(event) => onSetupChange({ ...setup, lectureCount: event.target.value })}
            />
          </label>
          <label>
            {t("builder.define.firstLectureDate")}
            <input
              type="date"
              value={setup.firstLectureDate}
              onChange={(event) =>
                onSetupChange({ ...setup, firstLectureDate: event.target.value })
              }
            />
          </label>
        </div>
      )}
      <button
        className="primary-action"
        disabled={!isReady || isCreating}
        type="button"
        onClick={onCreate}
      >
        {isCreating ? t("builder.define.creating") : t("builder.define.create")}
      </button>
      {isCreating ? <PendingStatus label={t("builder.define.creatingStatus")} /> : null}
    </section>
  );
}
