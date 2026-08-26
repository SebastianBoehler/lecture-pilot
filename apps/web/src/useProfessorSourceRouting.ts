import { useCallback, useState } from "react";

import { confirmSourceRouting, getSourceRouting, proposeSourceRouting } from "./professorApi";
import type { CourseSourceRoutingManifest, LoginSession, SourceRouteRole } from "./types";

export function useProfessorSourceRouting(session: LoginSession) {
  const [routing, setRouting] = useState<CourseSourceRoutingManifest | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  const load = useCallback(
    async (courseId: string) => {
      try {
        const result = await getSourceRouting(courseId, session);
        setRouting(result);
        setUnavailable(false);
        return result;
      } catch (error) {
        setRouting(null);
        setUnavailable(true);
        throw error;
      }
    },
    [session],
  );

  const reset = useCallback(() => {
    setRouting(null);
    setUnavailable(false);
  }, []);

  const regenerate = useCallback(
    async (courseId: string) => {
      const result = await proposeSourceRouting(courseId, session, true);
      setRouting(result);
      setUnavailable(false);
      return result;
    },
    [session],
  );

  const propose = useCallback(
    async (courseId: string) => {
      const result = await proposeSourceRouting(courseId, session);
      setRouting(result);
      setUnavailable(false);
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
      setUnavailable(false);
      return result;
    },
    [routing, session],
  );

  return { confirm, load, propose, regenerate, reset, routing, unavailable, updateRoute };
}
