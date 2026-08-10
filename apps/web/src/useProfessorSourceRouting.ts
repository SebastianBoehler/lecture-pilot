import { useCallback, useState } from "react";

import { confirmSourceRouting, proposeSourceRouting } from "./professorApi";
import type { CourseSourceRoutingManifest, LoginSession, SourceRouteRole } from "./types";

export function useProfessorSourceRouting(session: LoginSession) {
  const [routing, setRouting] = useState<CourseSourceRoutingManifest | null>(null);

  const load = useCallback(
    async (courseId: string) => {
      const result = await proposeSourceRouting(courseId, session);
      setRouting(result);
      return result;
    },
    [session],
  );

  const reset = useCallback(() => setRouting(null), []);

  const regenerate = useCallback(
    async (courseId: string) => {
      const result = await proposeSourceRouting(courseId, session, true);
      setRouting(result);
      return result;
    },
    [session],
  );

  const updateRoute = useCallback(
    (path: string, role: SourceRouteRole, lectureId: string | null) => {
      setRouting((current) =>
        current
          ? {
              ...current,
              confirmed: false,
              routes: current.routes.map((route) =>
                route.path === path
                  ? { ...route, role, lecture_id: role === "lecture" ? lectureId : null }
                  : route,
              ),
            }
          : current,
      );
    },
    [],
  );

  const confirm = useCallback(
    async (courseId: string) => {
      if (!routing) throw new Error("Load source routing before confirming it.");
      const result = await confirmSourceRouting(courseId, routing, session);
      setRouting(result);
      return result;
    },
    [routing, session],
  );

  return { confirm, load, regenerate, reset, routing, updateRoute };
}
