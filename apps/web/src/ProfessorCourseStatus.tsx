import { useI18n } from "./i18n";
import type { ManagedCourseWorkspaceResult } from "./types";

export function ProfessorCourseStatus({ workspace }: { workspace: ManagedCourseWorkspaceResult }) {
  const { t } = useI18n();
  const legacy = Boolean(workspace.legacyLectureIds?.length);
  const privateCourse =
    workspace.accessSummary.default_rule.audience === "instructors_only" &&
    workspace.accessSummary.lectures.every(
      (lecture) => lecture.rule.audience === "instructors_only",
    );
  if (!legacy && !privateCourse) return null;
  return (
    <div className="created-course-status">
      {privateCourse ? <strong>{t("courseAccess.audience.privateShort")}</strong> : null}
      {legacy ? <strong>{t("courseAccess.status.legacy")}</strong> : null}
      {legacy ? <p>{t("courseAccess.status.legacyHelp")}</p> : null}
    </div>
  );
}
