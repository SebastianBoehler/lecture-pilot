import type { CourseSourceRoute } from "./types";

export const SOURCE_ROUTE_PAGE_SIZE = 100;
export type SourceRouteScope = "assigned" | "excluded" | "all";

export type SourceRouteFilters = {
  scope: SourceRouteScope;
  query: string;
  kind: string;
  lectureId: string;
};

export function sourceRouteCounts(routes: CourseSourceRoute[]) {
  const lecture = routes.filter((route) => route.role === "lecture").length;
  const courseWide = routes.filter((route) => route.role === "course_wide").length;
  const excluded = routes.length - lecture - courseWide;
  return { assigned: lecture + courseWide, courseWide, excluded, lecture, total: routes.length };
}

export function filterSourceRoutes(
  routes: CourseSourceRoute[],
  filters: SourceRouteFilters,
): CourseSourceRoute[] {
  const query = filters.query.trim().toLocaleLowerCase();
  return routes
    .filter((route) => {
      if (filters.scope === "assigned" && route.role === "excluded") return false;
      if (filters.scope === "excluded" && route.role !== "excluded") return false;
      if (filters.kind && route.kind !== filters.kind) return false;
      if (filters.lectureId === "course_wide" && route.role !== "course_wide") return false;
      if (
        filters.lectureId &&
        filters.lectureId !== "course_wide" &&
        route.lecture_id !== filters.lectureId
      ) {
        return false;
      }
      return !query || route.path.toLocaleLowerCase().includes(query);
    })
    .sort(compareRoutes);
}

export function lectureRouteCounts(routes: CourseSourceRoute[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const route of routes) {
    if (route.role === "lecture" && route.lecture_id) {
      counts.set(route.lecture_id, (counts.get(route.lecture_id) ?? 0) + 1);
    }
  }
  return counts;
}

function compareRoutes(left: CourseSourceRoute, right: CourseSourceRoute): number {
  const roleOrder = { lecture: 0, course_wide: 1, excluded: 2 };
  return (
    roleOrder[left.role] - roleOrder[right.role] ||
    (left.lecture_id ?? "").localeCompare(right.lecture_id ?? "") ||
    left.path.localeCompare(right.path)
  );
}
