import { useCallback, useEffect, useState } from "react";

import { refreshSession, SessionRefreshError } from "./sessionApi";
import type { LoginSession } from "../shared/types";

const loginSessionKey = "lecturepilot.loginSession";
const SESSION_CHECK_MS = 5 * 60_000;

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

  const [expired, setExpired] = useState(false);
  useEffect(() => {
    // Cookie sessions can expire mid-workflow; detect it before an upload or save fails.
    if (session?.auth_transport !== "cookie") return;
    let checking = false;
    const check = () => {
      if (checking || document.visibilityState === "hidden") return;
      checking = true;
      void refreshSession(session)
        .then(() => setExpired(false))
        .catch((error: unknown) => {
          if (error instanceof SessionRefreshError && error.status === 401) setExpired(true);
        })
        .finally(() => {
          checking = false;
        });
    };
    const timer = window.setInterval(check, SESSION_CHECK_MS);
    window.addEventListener("focus", check);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", check);
    };
  }, [session]);

  const setSession = useCallback((nextSession: LoginSession | null) => {
    writeStoredLoginSession(nextSession);
    setSessionState(nextSession);
    setExpired(false);
  }, []);

  return [session, setSession, restoring, expired] as const;
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
