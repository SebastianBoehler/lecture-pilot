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
    const value = window.sessionStorage.getItem(loginSessionKey);
    return value ? (JSON.parse(value) as LoginSession) : null;
  } catch {
    return null;
  }
}

function writeStoredLoginSession(session: LoginSession | null) {
  try {
    if (session) window.sessionStorage.setItem(loginSessionKey, JSON.stringify(session));
    else window.sessionStorage.removeItem(loginSessionKey);
  } catch {
    // Session storage is an enhancement; login still works for the current render.
  }
}
