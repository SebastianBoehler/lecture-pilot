import { useI18n } from "./i18n";
import { StepHeader } from "./ProfessorCourseBuilderParts";
import { lectureIdFromNumber } from "./professorWorkspaceActivation";
import type { CourseSourceRoutingManifest, LectureScheduleItem, SourceRouteRole } from "./types";

const ROLES: SourceRouteRole[] = ["lecture", "course_wide", "excluded"];

export function ProfessorSourceRoutingStep({
  isSaving,
  lectures,
  routing,
  onConfirm,
  onRouteChange,
}: {
  isSaving: boolean;
  lectures: LectureScheduleItem[];
  routing: CourseSourceRoutingManifest | null;
  onConfirm: () => void;
  onRouteChange: (path: string, role: SourceRouteRole, lectureId: string | null) => void;
}) {
  const { t } = useI18n();
  const lectureOptions = lectures.map((lecture) => ({
    id: lectureIdFromNumber(lecture.number),
    label: `${lecture.number} · ${lecture.title}`,
  }));
  return (
    <section className="flow-card">
      <StepHeader
        number="03"
        title={t("builder.sources.title")}
        done={Boolean(routing?.confirmed)}
      />
      <p className="flow-help">{t("builder.sources.help")}</p>
      <div
        aria-label={t("builder.sources.legendLabel")}
        className="source-routing-legend"
        role="list"
      >
        <div role="listitem">
          <strong>{t("builder.sources.role.lecture")}</strong>
          <span>{t("builder.sources.legend.lecture")}</span>
        </div>
        <div role="listitem">
          <strong>{t("builder.sources.role.courseWide")}</strong>
          <span>{t("builder.sources.legend.courseWide")}</span>
        </div>
        <div role="listitem">
          <strong>{t("builder.sources.role.excluded")}</strong>
          <span>{t("builder.sources.legend.excluded")}</span>
        </div>
      </div>
      <div
        aria-label={t("builder.sources.tableLabel")}
        className="source-routing-list"
        role="table"
      >
        <div className="source-routing-columns" role="row">
          <span role="columnheader">{t("builder.sources.column.file")}</span>
          <span role="columnheader">{t("builder.sources.column.use")}</span>
          <span role="columnheader">{t("builder.sources.column.lecture")}</span>
        </div>
        {routing?.routes.map((route) => (
          <div className="source-routing-row" key={route.path} role="row">
            <div className="source-routing-file" role="cell">
              <span className="source-routing-name" title={route.path}>
                {fileName(route.path)}
              </span>
              <span className="source-routing-meta">
                <span>{route.kind}</span>
                {fileDirectory(route.path) ? (
                  <span className="source-routing-directory">{fileDirectory(route.path)}</span>
                ) : null}
              </span>
            </div>
            <div className="source-routing-control" role="cell">
              <span aria-hidden="true" className="source-routing-mobile-label">
                {t("builder.sources.column.use")}
              </span>
              <select
                aria-label={t("builder.sources.routeLabel", { path: route.path })}
                value={route.role}
                onChange={(event) => {
                  const role = event.target.value as SourceRouteRole;
                  onRouteChange(
                    route.path,
                    role,
                    role === "lecture" ? (route.lecture_id ?? lectureOptions[0]?.id ?? null) : null,
                  );
                }}
              >
                {ROLES.map((role) => (
                  <option key={role} value={role}>
                    {roleLabel(role, t)}
                  </option>
                ))}
              </select>
            </div>
            {route.role === "lecture" ? (
              <div className="source-routing-control" role="cell">
                <span aria-hidden="true" className="source-routing-mobile-label">
                  {t("builder.sources.column.lecture")}
                </span>
                <select
                  aria-label={t("builder.sources.lectureLabel", { path: route.path })}
                  value={route.lecture_id ?? ""}
                  onChange={(event) =>
                    onRouteChange(route.path, "lecture", event.target.value || null)
                  }
                >
                  {lectureOptions.map((lecture) => (
                    <option key={lecture.id} value={lecture.id}>
                      {lecture.label}
                    </option>
                  ))}
                </select>
              </div>
            ) : (
              <span aria-hidden="true" className="source-routing-empty" role="cell">
                —
              </span>
            )}
          </div>
        ))}
      </div>
      <div className="flow-actions">
        <button
          className="primary-action"
          disabled={!routing?.routes.length || routing.confirmed || isSaving}
          type="button"
          onClick={onConfirm}
        >
          {isSaving ? t("builder.sources.confirming") : t("builder.sources.confirm")}
        </button>
      </div>
    </section>
  );
}

function roleLabel(role: SourceRouteRole, t: ReturnType<typeof useI18n>["t"]): string {
  if (role === "lecture") return t("builder.sources.role.lecture");
  if (role === "course_wide") return t("builder.sources.role.courseWide");
  return t("builder.sources.role.excluded");
}

function fileName(path: string): string {
  return path.split("/").at(-1) ?? path;
}

function fileDirectory(path: string): string {
  const separator = path.lastIndexOf("/");
  return separator < 0 ? "" : path.slice(0, separator + 1);
}
