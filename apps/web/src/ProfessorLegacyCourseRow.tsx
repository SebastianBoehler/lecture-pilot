import { Archive } from "lucide-react";

import { useI18n } from "./i18n";
import type { ManagedCourseWorkspaceResult } from "./types";

export function ProfessorLegacyCourseRow({
  workspace,
  deleting,
  onDelete,
}: {
  workspace: ManagedCourseWorkspaceResult;
  deleting: boolean;
  onDelete: (courseId: string) => void;
}) {
  const { t } = useI18n();
  const privateCourse =
    workspace.accessSummary.lectures.every(
      (lecture) => lecture.rule.audience === "instructors_only",
    ) && workspace.accessSummary.default_rule.audience === "instructors_only";
  return (
    <article className="created-course-row is-legacy" data-state="disabled">
      <div className="created-course-summary">
        <div className="created-course-title">
          <strong>{workspace.course.title}</strong>
          <span>{workspace.course.term}</span>
          <span>{t("professor.configuredLectures", { count: workspace.lectures.length })}</span>
        </div>
        <div className="created-course-meta legacy-course-state">
          <Archive aria-hidden="true" size={20} />
          <div>
            <strong>{t("courseAccess.status.legacyDisabled")}</strong>
            <span>{t("courseAccess.status.legacyRecreate")}</span>
            {privateCourse ? <span>{t("courseAccess.audience.privateShort")}</span> : null}
          </div>
        </div>
        <div className="created-course-actions">
          <button
            className="refresh-button delete-course-button"
            disabled={deleting}
            type="button"
            aria-label={t("professor.deleteCourse", { course: workspace.course.title })}
            onClick={() => onDelete(workspace.course.id)}
          >
            {deleting ? t("professor.deleting") : t("professor.delete")}
          </button>
        </div>
      </div>
      <p>{t("courseAccess.status.legacyHelp")}</p>
    </article>
  );
}
