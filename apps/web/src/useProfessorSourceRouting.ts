import { useCallback, useRef, useState } from "react";

import {
  SourceRoutingRequestError,
  confirmSourceRouting,
  getSourceRouting,
  proposeSourceRouting,
} from "./professorApi";
import { hasNoAssignedEvidence } from "./sourceRoutingView";
import type { CourseSourceRoutingManifest, LoginSession, SourceRouteRole } from "./types";

type RoutingStatus = "current" | "stale" | "unavailable";

export function useProfessorSourceRouting(session: LoginSession) {
  const [routing, setRouting] = useState<CourseSourceRoutingManifest | null>(null);
  const [status, setStatus] = useState<RoutingStatus>("unavailable");
  const hadConfirmedAuthority = useRef(false);

  const load = useCallback(
    async (courseId: string) => {
      try {
        const result = await getSourceRouting(courseId, session);
        setRouting(result);
        hadConfirmedAuthority.current = hasConfirmedAuthority(result);
        setStatus("current");
        return result;
      } catch (error) {
        setRouting(null);
        setStatus(
          error instanceof SourceRoutingRequestError &&
            error.status === 409 &&
            hadConfirmedAuthority.current
            ? "stale"
            : "unavailable",
        );
        throw error;
      }
    },
    [session],
  );

  const reset = useCallback(() => {
    setRouting(null);
    hadConfirmedAuthority.current = false;
    setStatus("unavailable");
  }, []);

  const regenerate = useCallback(
    async (courseId: string) => {
      const result = await proposeSourceRouting(courseId, session, true);
      setRouting(result);
      hadConfirmedAuthority.current = hasConfirmedAuthority(result);
      setStatus("current");
      return result;
    },
    [session],
  );

  const propose = useCallback(
    async (courseId: string) => {
      const result = await proposeSourceRouting(courseId, session);
      setRouting(result);
      hadConfirmedAuthority.current = hasConfirmedAuthority(result);
      setStatus("current");
      return result;
    },
    [session],
  );

  const updateRoute = useCallback(
    (path: string, role: SourceRouteRole, lectureId: string | null) => {
      hadConfirmedAuthority.current = false;
      setStatus("current");
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
      hadConfirmedAuthority.current = hasConfirmedAuthority(result);
      setStatus("current");
      return result;
    },
    [routing, session],
  );

  return { confirm, load, propose, regenerate, reset, routing, status, updateRoute };
}

function hasConfirmedAuthority(routing: CourseSourceRoutingManifest) {
  return routing.confirmed && !hasNoAssignedEvidence(routing.routes);
}
