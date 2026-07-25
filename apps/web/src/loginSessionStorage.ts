import { useCallback, useEffect, useState } from "react";

import { refreshSession, SessionRefreshError } from "./sessionApi";
import type { LoginSession } from "./types";

const loginSessionKey = "lecturepilot.loginSession";

export function useStoredLoginSession() {
  const [initialSession] = useState<LoginSession | null>(readStoredLoginSession);
  const shouldRestore = initialSession?.auth_transport === "cookie";
  const [session, setSessionState] = useState<LoginSession | null>(
    shouldRestore ? null : initialSession,
  );
  const [restoring, setRestoring] = useState(shouldRestore);

  useEffect(() => {
    if (!shouldRestore || !initialSession) return;
    const controller = new AbortController();
    void refreshSession(initialSession, controller.signal)
      .then((refreshed) => {
        if (controller.signal.aborted) return;
        writeStoredLoginSession(refreshed);
        setSessionState(refreshed);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        if (error instanceof SessionRefreshError && error.status === 401) {
          writeStoredLoginSession(null);
          setSessionState(null);
          return;
        }
        setSessionState(initialSession);
      })
      .finally(() => {
        if (!controller.signal.aborted) setRestoring(false);
      });
    return () => controller.abort();
  }, [initialSession, shouldRestore]);

  const setSession = useCallback((nextSession: LoginSession | null) => {
    writeStoredLoginSession(nextSession);
    setSessionState(nextSession);
  }, []);

  return [session, setSession, restoring] as const;
}

function readStoredLoginSession() {
  try {
    const storedValue = window.localStorage.getItem(loginSessionKey);
    return storedValue ? (JSON.parse(storedValue) as LoginSession) : null;
  } catch {
    return null;
  }
}

function writeStoredLoginSession(session: LoginSession | null) {
  try {
    window.sessionStorage.removeItem(loginSessionKey);
    if (session) {
      window.localStorage.setItem(loginSessionKey, JSON.stringify(withoutAccessToken(session)));
    } else {
      window.localStorage.removeItem(loginSessionKey);
    }
  } catch {
    // Storage is an enhancement; login still works for the current render.
  }
}

function withoutAccessToken(session: LoginSession): LoginSession {
  const { access_token: _accessToken, ...persistedSession } = session;
  return persistedSession;
}
