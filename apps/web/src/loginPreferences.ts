import { useState } from "react";

export type LoginAudience = "student" | "professor";

const audienceKey = "lecturepilot.loginAudience";
const identifierKeys: Record<LoginAudience, string> = {
  student: "lecturepilot.rememberedStudentUsername",
  professor: "lecturepilot.rememberedProfessorEmail",
};
const rememberChoiceKeys: Record<LoginAudience, string> = {
  student: "lecturepilot.rememberStudentUsernameEnabled",
  professor: "lecturepilot.rememberProfessorEmailEnabled",
};

export function readStoredLoginAudience(): LoginAudience {
  try {
    return window.localStorage.getItem(audienceKey) === "professor" ? "professor" : "student";
  } catch {
    return "student";
  }
}

export function writeStoredLoginAudience(audience: LoginAudience) {
  try {
    window.localStorage.setItem(audienceKey, audience);
  } catch {
    // Remembering the selected account type is optional.
  }
}

export function useRememberedLoginIdentifier(audience: LoginAudience) {
  const [initialPreference] = useState(() => readRememberedLoginPreference(audience));
  const [identifier, setIdentifier] = useState(initialPreference.identifier);
  const [remember, setRememberState] = useState(initialPreference.remember);

  function setRemember(nextRemember: boolean) {
    setRememberState(nextRemember);
    writeRememberChoice(audience, nextRemember);
    if (!nextRemember) removeRememberedIdentifier(audience);
  }

  function persistRememberedIdentifier() {
    writeRememberChoice(audience, remember);
    if (remember) writeRememberedIdentifier(audience, identifier);
    else removeRememberedIdentifier(audience);
  }

  return {
    identifier,
    persistRememberedIdentifier,
    remember,
    setIdentifier,
    setRemember,
  };
}

function readRememberedLoginPreference(audience: LoginAudience) {
  const remember = readRememberChoice(audience);
  return {
    identifier: remember ? readRememberedIdentifier(audience) : "",
    remember,
  };
}

function readRememberChoice(audience: LoginAudience) {
  try {
    return window.localStorage.getItem(rememberChoiceKeys[audience]) !== "false";
  } catch {
    return true;
  }
}

function writeRememberChoice(audience: LoginAudience, remember: boolean) {
  try {
    window.localStorage.setItem(rememberChoiceKeys[audience], String(remember));
  } catch {
    // Remembering the choice is optional; login still works.
  }
}

function readRememberedIdentifier(audience: LoginAudience) {
  try {
    return (window.localStorage.getItem(identifierKeys[audience]) ?? "").slice(0, 254);
  } catch {
    return "";
  }
}

function writeRememberedIdentifier(audience: LoginAudience, identifier: string) {
  const normalized = identifier.trim().slice(0, 254);
  if (!normalized) return removeRememberedIdentifier(audience);
  try {
    window.localStorage.setItem(identifierKeys[audience], normalized);
  } catch {
    // Remembering the identifier is optional; login still works.
  }
}

function removeRememberedIdentifier(audience: LoginAudience) {
  try {
    window.localStorage.removeItem(identifierKeys[audience]);
  } catch {
    // Storage is an enhancement; login still works.
  }
}
