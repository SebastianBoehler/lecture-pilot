import { useEffect } from "react";

import { refreshSession } from "./sessionApi";
import type { LoginSession } from "./types";

const POLL_INTERVAL_MS = 750;
const SYNC_TIMEOUT_MS = 60_000;

export function useUniversityCourseSync(
  session: LoginSession | null,
  setSession: (session: LoginSession | null) => void,
) {
  useEffect(() => {
    if (!session || session.university_course_sync_status !== "loading") return;

    const activeSession = session;
    const controller = new AbortController();
    const deadline = Date.now() + SYNC_TIMEOUT_MS;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      if (Date.now() >= deadline) {
        setSession({ ...activeSession, university_course_sync_status: "error" });
        return;
      }
      try {
        const refreshed = await refreshSession(activeSession, controller.signal);
        if (controller.signal.aborted) return;
        if (refreshed.university_course_sync_status !== "loading") {
          setSession(refreshed);
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
  }, [session, setSession]);
}
