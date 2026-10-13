import { useCallback, useEffect, useState } from "react";

import { ApiRequestError } from "../shared/apiRequest";
import { errorMessage } from "../shared/errorMessage";
import { pollUntil } from "../shared/polling";
import type { LoginSession } from "../shared/types";
import { getCourseLectureStates } from "./courseLectureStatesApi";
import { isLectureBusy } from "./courseLectureStatus";
import type { CourseLectureStates } from "./courseLectureStateTypes";

const POLL_FIRST_MS = 2_000;
const POLL_MAX_MS = 15_000;
const POLL_TIMEOUT_MS = 2 * 60 * 60 * 1000;

/** Loads lecture states and polls them only while goals are proposed or drafts generate. */
export function useCourseLectureStates(courseId: string, session: LoginSession) {
  const [states, setStates] = useState<CourseLectureStates | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setStates(await getCourseLectureStates(courseId, session));
      setError(null);
    } catch (cause) {
      setError(errorMessage(cause, "Lecture states could not be loaded."));
    }
  }, [courseId, session]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const busy = Boolean(states?.lectures.some(isLectureBusy));
  useEffect(() => {
    if (!busy) return;
    const controller = new AbortController();
    pollUntil({
      initialDelayMs: POLL_FIRST_MS,
      maxDelayMs: POLL_MAX_MS,
      timeoutMs: POLL_TIMEOUT_MS,
      signal: controller.signal,
      poll: async () => {
        let next: CourseLectureStates;
        try {
          next = await getCourseLectureStates(courseId, session);
        } catch (cause) {
          // Network blips and overloaded hosts are waited out; a rejected request stops polling.
          if (!isTransient(cause)) throw cause;
          return { done: false };
        }
        if (controller.signal.aborted) return { done: true, value: null };
        setStates(next);
        setError(null);
        return next.lectures.some(isLectureBusy) ? { done: false } : { done: true, value: null };
      },
    }).catch((cause: unknown) => {
      if (controller.signal.aborted) return;
      setError(errorMessage(cause, "Lecture states could not be loaded."));
    });
    return () => controller.abort();
  }, [busy, courseId, session]);

  return { states, error, refresh, busy };
}

function isTransient(cause: unknown) {
  if (!(cause instanceof ApiRequestError)) return true;
  return cause.status === 429 || cause.status >= 500;
}
