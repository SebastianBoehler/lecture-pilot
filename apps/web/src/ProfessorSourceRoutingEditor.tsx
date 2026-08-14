import { useEffect, useMemo, useState } from "react";

import { useI18n } from "./i18n";
import type { SourceRoutingLectureOption } from "./ProfessorSourceRoutingStep";
import {
  filterSourceRoutes,
  lectureRouteCounts,
  SOURCE_ROUTE_PAGE_SIZE,
  sourceRouteCounts,
  type SourceRouteScope,
} from "./sourceRoutingView";
import type { CourseSourceRoute, SourceProcessingStatus, SourceRouteRole } from "./types";

const ROLES: SourceRouteRole[] = ["lecture", "course_wide", "excluded"];

export function ProfessorSourceRoutingEditor({
  lectureOptions,
  routes,
  onRouteChange,
}: {
  lectureOptions: SourceRoutingLectureOption[];
  routes: CourseSourceRoute[];
  onRouteChange: (path: string, role: SourceRouteRole, lectureId: string | null) => void;
}) {
  const { t } = useI18n();
  const counts = useMemo(() => sourceRouteCounts(routes), [routes]);
  const lectureCounts = useMemo(() => lectureRouteCounts(routes), [routes]);
  const kinds = useMemo(
    () => Array.from(new Set(routes.map((route) => route.kind))).sort(),
    [routes],
  );
  const [scope, setScope] = useState<SourceRouteScope>("assigned");
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("");
  const [lectureId, setLectureId] = useState("");
  const [page, setPage] = useState(0);
  const filteredRoutes = useMemo(
    () => filterSourceRoutes(routes, { kind, lectureId, query, scope }),
    [kind, lectureId, query, routes, scope],
  );
  const pageCount = Math.max(1, Math.ceil(filteredRoutes.length / SOURCE_ROUTE_PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const pageStart = safePage * SOURCE_ROUTE_PAGE_SIZE;
  const visibleRoutes = filteredRoutes.slice(pageStart, pageStart + SOURCE_ROUTE_PAGE_SIZE);
  useEffect(() => setPage(0), [kind, lectureId, query, scope]);
  return (
    <div className="source-routing-editor">
      <div
        aria-label={t("builder.sources.legendLabel")}
        className="source-routing-legend"
        role="list"
      >
        {(["lecture", "courseWide", "excluded"] as const).map((role) => (
          <div key={role} role="listitem">
            <strong>{t(`builder.sources.role.${role}`)}</strong>
            <span>{t(`builder.sources.legend.${role}`)}</span>
          </div>
        ))}
      </div>
      <div className="source-routing-summary">
        <div aria-label={t("builder.sources.scopeLabel")} className="source-routing-scopes">
          <ScopeButton
            active={scope === "assigned"}
            label={t("builder.sources.scope.assigned", { count: counts.assigned })}
            onClick={() => setScope("assigned")}
          />
          <ScopeButton
            active={scope === "excluded"}
            label={t("builder.sources.scope.excluded", { count: counts.excluded })}
            onClick={() => setScope("excluded")}
          />
          <ScopeButton
            active={scope === "all"}
            label={t("builder.sources.scope.all", { count: counts.total })}
            onClick={() => setScope("all")}
          />
        </div>
        <div className="source-routing-filters">
          <label>
            <span>{t("builder.sources.search")}</span>
            <input
              aria-label={t("builder.sources.search")}
              placeholder={t("builder.sources.searchPlaceholder")}
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <label>
            <span>{t("builder.sources.kind")}</span>
            <select value={kind} onChange={(event) => setKind(event.target.value)}>
              <option value="">{t("builder.sources.allKinds")}</option>
              {kinds.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>{t("builder.sources.lectureFilter")}</span>
            <select value={lectureId} onChange={(event) => setLectureId(event.target.value)}>
              <option value="">{t("builder.sources.allLectures")}</option>
              <option value="course_wide">{t("builder.sources.role.courseWide")}</option>
              {lectureOptions.map((lecture) => (
                <option key={lecture.id} value={lecture.id}>
                  {lecture.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div aria-label={t("builder.sources.coverageLabel")} className="source-routing-coverage">
          {lectureOptions.map((lecture) => (
            <button
              aria-pressed={lectureId === lecture.id}
              key={lecture.id}
              type="button"
              onClick={() => {
                setLectureId((current) => (current === lecture.id ? "" : lecture.id));
                setScope("assigned");
              }}
            >
              <span>{lecture.label}</span>
              <strong>{lectureCounts.get(lecture.id) ?? 0}</strong>
            </button>
          ))}
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
        {visibleRoutes.map((route) => (
          <div className="source-routing-row" key={route.path} role="row">
            <div className="source-routing-file" role="cell">
              <span className="source-routing-name" title={route.path}>
                {fileName(route.path)}
              </span>
              <span className="source-routing-meta">
                <span>{route.kind}</span>
                <span className={`source-processing-status is-${routeStatus(route)}`}>
                  {statusLabel(routeStatus(route), t)}
                </span>
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
      {filteredRoutes.length ? (
        <div className="source-routing-pagination">
          <span>
            {t("builder.sources.showing", {
              end: Math.min(pageStart + SOURCE_ROUTE_PAGE_SIZE, filteredRoutes.length),
              start: pageStart + 1,
              total: filteredRoutes.length,
            })}
          </span>
          <div>
            <button disabled={safePage === 0} type="button" onClick={() => setPage(safePage - 1)}>
              {t("builder.sources.previous")}
            </button>
            <button
              disabled={safePage >= pageCount - 1}
              type="button"
              onClick={() => setPage(safePage + 1)}
            >
              {t("builder.sources.next")}
            </button>
          </div>
        </div>
      ) : (
        <p className="source-routing-empty-state">{t("builder.sources.noMatches")}</p>
      )}
    </div>
  );
}

function ScopeButton({
  active,
  label,
  onClick,
}: {
  active: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button aria-pressed={active} type="button" onClick={onClick}>
      {label}
    </button>
  );
}

function roleLabel(role: SourceRouteRole, t: ReturnType<typeof useI18n>["t"]): string {
  if (role === "lecture") return t("builder.sources.role.lecture");
  if (role === "course_wide") return t("builder.sources.role.courseWide");
  return t("builder.sources.role.excluded");
}

function routeStatus(route: CourseSourceRoute): SourceProcessingStatus | "excluded" {
  return route.role === "excluded" ? "excluded" : (route.processing_status ?? "preserved");
}

function statusLabel(
  status: SourceProcessingStatus | "excluded",
  t: ReturnType<typeof useI18n>["t"],
): string {
  if (status === "converted") return t("builder.sources.status.converted");
  if (status === "ocr_needed") return t("builder.sources.status.ocrNeeded");
  if (status === "excluded") return t("builder.sources.status.excluded");
  return t("builder.sources.status.preserved");
}

function fileName(path: string): string {
  return path.split("/").at(-1) ?? path;
}
function fileDirectory(path: string): string {
  const separator = path.lastIndexOf("/");
  return separator < 0 ? "" : path.slice(0, separator + 1);
}
