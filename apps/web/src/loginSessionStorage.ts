import { useState } from "react";

import type { LoginSession } from "./types";

const loginSessionKey = "lecturepilot.loginSession";

export function useStoredLoginSession() {
  const [session, setSessionState] = useState<LoginSession | null>(readStoredLoginSession);

  function setSession(nextSession: LoginSession | null) {
    writeStoredLoginSession(nextSession);
    setSessionState(nextSession);
  }

  return [session, setSession] as const;
}

function readStoredLoginSession() {
  try {
    const sessionValue = window.sessionStorage.getItem(loginSessionKey);
    if (sessionValue) return JSON.parse(sessionValue) as LoginSession;
    const storedValue = window.localStorage.getItem(loginSessionKey);
    return storedValue ? (JSON.parse(storedValue) as LoginSession) : null;
  } catch {
    return null;
  }
}

function writeStoredLoginSession(session: LoginSession | null) {
  try {
    if (session) {
      const payload = JSON.stringify(session);
      window.sessionStorage.setItem(loginSessionKey, payload);
      window.localStorage.setItem(loginSessionKey, JSON.stringify(withoutAccessToken(session)));
    } else {
      window.sessionStorage.removeItem(loginSessionKey);
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
