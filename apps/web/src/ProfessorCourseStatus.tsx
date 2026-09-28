import { useI18n } from "./i18n";
import type { ManagedCourseWorkspaceResult } from "./types";

export function ProfessorCourseStatus({ workspace }: { workspace: ManagedCourseWorkspaceResult }) {
  const { t } = useI18n();
  const privateCourse =
    workspace.accessSummary.default_rule.audience === "instructors_only" &&
    workspace.accessSummary.lectures.every(
      (lecture) => lecture.rule.audience === "instructors_only",
    );
  if (!privateCourse) return null;
  return (
    <div className="created-course-status">
      {privateCourse ? <strong>{t("courseAccess.audience.privateShort")}</strong> : null}
    </div>
  );
}
