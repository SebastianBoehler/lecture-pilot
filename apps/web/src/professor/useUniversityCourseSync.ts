import { useEffect, useRef } from "react";

import { pollUntil, PollTimeoutError } from "../shared/polling";
import { refreshSession } from "../auth/sessionApi";
import type { LoginSession } from "../shared/types";

const FIRST_POLL_MS = 2_000;
const MAX_POLL_MS = 8_000;
const SYNC_TIMEOUT_MS = 60_000;

export function useUniversityCourseSync(
  session: LoginSession | null,
  setSession: (session: LoginSession | null) => void,
) {
  const sessionRef = useRef(session);
  const syncStatus = session?.university_course_sync_status;
  const username = session?.username;

  useEffect(() => {
    sessionRef.current = session;
  }, [session]);

  useEffect(() => {
    const activeSession = sessionRef.current;
    if (!activeSession || syncStatus !== "loading") return;
    const pollingSession: LoginSession = activeSession;

    const controller = new AbortController();
    let latestSession = activeSession;

    pollUntil({
      initialDelayMs: FIRST_POLL_MS,
      maxDelayMs: MAX_POLL_MS,
      timeoutMs: SYNC_TIMEOUT_MS,
      signal: controller.signal,
      poll: async (signal) => {
        try {
          const refreshed = await refreshSession(pollingSession, signal);
          if (signal?.aborted) return { done: true, value: undefined };
          latestSession = refreshed;
          setSession(refreshed);
          return refreshed.university_course_sync_status === "loading"
            ? { done: false }
            : { done: true, value: undefined };
        } catch (error) {
          if (signal?.aborted) throw error;
          return { done: false };
        }
      },
    }).catch((error: unknown) => {
      if (error instanceof PollTimeoutError) {
        setSession({ ...latestSession, university_course_sync_status: "error" });
      }
    });
    return () => controller.abort();
  }, [setSession, syncStatus, username]);
}
