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
