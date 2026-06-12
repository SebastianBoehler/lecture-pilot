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
    const value = window.sessionStorage.getItem(loginSessionKey) ?? window.localStorage.getItem(loginSessionKey);
    return value ? (JSON.parse(value) as LoginSession) : null;
  } catch {
    return null;
  }
}

function writeStoredLoginSession(session: LoginSession | null) {
  try {
    if (session) {
      const payload = JSON.stringify(session);
      window.sessionStorage.setItem(loginSessionKey, payload);
      window.localStorage.setItem(loginSessionKey, payload);
    } else {
      window.sessionStorage.removeItem(loginSessionKey);
      window.localStorage.removeItem(loginSessionKey);
    }
  } catch {
    // Storage is an enhancement; login still works for the current render.
  }
}
