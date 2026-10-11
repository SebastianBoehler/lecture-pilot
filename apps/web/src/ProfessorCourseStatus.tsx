import { useI18n } from "./i18n";
import type { ManagedCourseWorkspaceResult } from "./types";

export type CourseSetupState = {
  kind: "setup" | "partial" | "published";
  published: number;
  total: number;
};

export function courseSetupState(workspace: ManagedCourseWorkspaceResult): CourseSetupState {
  const total = workspace.lectures.length;
  const published = workspace.accessSummary.lectures.filter(
    (lecture) => lecture.content_ready,
  ).length;
  if (!total || !published) return { kind: "setup", published, total };
  return { kind: published < total ? "partial" : "published", published, total };
}

export function ProfessorCourseStatus({ workspace }: { workspace: ManagedCourseWorkspaceResult }) {
  const { t } = useI18n();
  const setup = courseSetupState(workspace);
  const privateCourse =
    workspace.accessSummary.default_rule.audience === "instructors_only" &&
    workspace.accessSummary.lectures.every(
      (lecture) => lecture.rule.audience === "instructors_only",
    );
  return (
    <div className="created-course-status">
      <strong data-setup-state={setup.kind}>
        {setup.kind === "setup"
          ? t("professor.setup.incomplete")
          : setup.kind === "partial"
            ? t("professor.setup.partial", { published: setup.published, total: setup.total })
            : t("professor.setup.published")}
      </strong>
      {privateCourse ? <strong>{t("courseAccess.audience.privateShort")}</strong> : null}
    </div>
  );
}
