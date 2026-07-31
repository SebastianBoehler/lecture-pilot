import { useI18n } from "./i18n";
import { StepHeader } from "./ProfessorCourseBuilderParts";
import { lectureIdFromNumber } from "./professorWorkspaceActivation";
import type { CourseSourceRoutingManifest, LectureScheduleItem, SourceRouteRole } from "./types";

const ROLES: SourceRouteRole[] = ["lecture", "course_wide", "reference_only", "excluded"];

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
      <p className="source-routing-note">{t("builder.sources.referenceHelp")}</p>
      <div className="source-routing-list">
        {routing?.routes.map((route) => (
          <div className="source-routing-row" key={route.path}>
            <div className="source-routing-file">
              <strong title={route.path}>{route.path}</strong>
              <span>{route.kind}</span>
            </div>
            <label>
              <span className="sr-only">
                {t("builder.sources.routeLabel", { path: route.path })}
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
            </label>
            {route.role === "lecture" ? (
              <label>
                <span className="sr-only">
                  {t("builder.sources.lectureLabel", { path: route.path })}
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
              </label>
            ) : null}
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
  if (role === "reference_only") return t("builder.sources.role.referenceOnly");
  return t("builder.sources.role.excluded");
}
