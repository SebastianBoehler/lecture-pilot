import { useCallback, useLayoutEffect, useRef, useState } from "react";

import {
  SourceRoutingRequestError,
  confirmSourceRouting,
  getSourceRouting,
  proposeSourceRouting,
} from "./professorApi";
import { hasNoAssignedEvidence } from "./sourceRoutingView";
import type { CourseSourceRoutingManifest, LoginSession, SourceRouteRole } from "./types";

type RoutingStatus = "current" | "stale" | "unavailable";
type ActiveRouting = {
  courseId: string | null;
  epoch: number;
  hadConfirmedAuthority: boolean;
  identityKey: string;
};
type RoutingOperation = Pick<ActiveRouting, "courseId" | "epoch" | "identityKey">;

export function useProfessorSourceRouting(session: LoginSession) {
  const identityKey = JSON.stringify([session.tenant_id ?? "", session.username]);
  const [routing, setRouting] = useState<CourseSourceRoutingManifest | null>(null);
  const [status, setStatus] = useState<RoutingStatus>("unavailable");
  const active = useRef<ActiveRouting>({
    courseId: null,
    epoch: 0,
    hadConfirmedAuthority: false,
    identityKey,
  });
  const invalidate = useCallback((nextIdentityKey: string) => {
    active.current = {
      courseId: null,
      epoch: active.current.epoch + 1,
      hadConfirmedAuthority: false,
      identityKey: nextIdentityKey,
    };
    setRouting(null);
    setStatus("unavailable");
  }, []);
  const beginOperation = useCallback(
    (courseId: string): RoutingOperation => {
      if (active.current.identityKey !== identityKey || active.current.courseId !== courseId) {
        active.current = {
          courseId,
          epoch: active.current.epoch + 1,
          hadConfirmedAuthority: false,
          identityKey,
        };
        setRouting(null);
        setStatus("unavailable");
      }
      active.current.epoch += 1;
      return {
        courseId,
        epoch: active.current.epoch,
        identityKey,
      };
    },
    [identityKey],
  );

  useLayoutEffect(() => {
    if (active.current.identityKey === identityKey) return;
    invalidate(identityKey);
  }, [identityKey, invalidate]);

  const load = useCallback(
    async (courseId: string) => {
      const operation = beginOperation(courseId);
      try {
        const result = await getSourceRouting(courseId, session);
        if (isCurrent(operation)) commitRouting(result);
        return result;
      } catch (error) {
        if (isCurrent(operation)) commitError(error);
        throw error;
      }
    },
    [beginOperation, session],
  );

  const reset = useCallback(() => {
    invalidate(identityKey);
  }, [identityKey, invalidate]);

  const regenerate = useCallback(
    async (courseId: string) => {
      const operation = beginOperation(courseId);
      const result = await proposeSourceRouting(courseId, session, true);
      if (isCurrent(operation)) commitRouting(result);
      return result;
    },
    [beginOperation, session],
  );

  const propose = useCallback(
    async (courseId: string) => {
      const operation = beginOperation(courseId);
      const result = await proposeSourceRouting(courseId, session);
      if (isCurrent(operation)) commitRouting(result);
      return result;
    },
    [beginOperation, session],
  );

  const updateRoute = useCallback(
    (path: string, role: SourceRouteRole, lectureId: string | null) => {
      active.current.hadConfirmedAuthority = false;
      active.current.epoch += 1;
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
      if (!routing || routing.course_id !== courseId)
        throw new Error("Load source routing before confirming it.");
      const operation = beginOperation(courseId);
      const result = await confirmSourceRouting(courseId, routing, session);
      if (isCurrent(operation)) commitRouting(result);
      return result;
    },
    [beginOperation, routing, session],
  );

  return { confirm, load, propose, regenerate, reset, routing, status, updateRoute };

  function isCurrent(operation: RoutingOperation) {
    return (
      active.current.courseId === operation.courseId &&
      active.current.epoch === operation.epoch &&
      active.current.identityKey === operation.identityKey
    );
  }

  function commitRouting(result: CourseSourceRoutingManifest) {
    setRouting(result);
    active.current.hadConfirmedAuthority = hasConfirmedAuthority(result);
    setStatus("current");
  }

  function commitError(error: unknown) {
    setRouting(null);
    setStatus(
      error instanceof SourceRoutingRequestError &&
        error.status === 409 &&
        active.current.hadConfirmedAuthority
        ? "stale"
        : "unavailable",
    );
  }
}

function hasConfirmedAuthority(routing: CourseSourceRoutingManifest) {
  return routing.confirmed && !hasNoAssignedEvidence(routing.routes);
}
