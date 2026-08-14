import { useEffect, useRef } from "react";

import { refreshSession } from "./sessionApi";
import type { LoginSession } from "./types";

const POLL_INTERVAL_MS = 750;
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
    const deadline = Date.now() + SYNC_TIMEOUT_MS;
    let latestSession = activeSession;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      if (Date.now() >= deadline) {
        setSession({ ...latestSession, university_course_sync_status: "error" });
        return;
      }
      try {
        const refreshed = await refreshSession(pollingSession, controller.signal);
        if (controller.signal.aborted) return;
        latestSession = refreshed;
        setSession(refreshed);
        if (refreshed.university_course_sync_status !== "loading") {
          return;
        }
      } catch {
        if (controller.signal.aborted) return;
      }
      timer = setTimeout(poll, POLL_INTERVAL_MS);
    }

    timer = setTimeout(poll, POLL_INTERVAL_MS);
    return () => {
      controller.abort();
      if (timer) clearTimeout(timer);
    };
  }, [setSession, syncStatus, username]);
}
