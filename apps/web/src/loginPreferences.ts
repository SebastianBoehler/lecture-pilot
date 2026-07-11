import { useState } from "react";

const identifierKey = "lecturepilot.rememberedStudentUsername";
const rememberChoiceKey = "lecturepilot.rememberStudentUsernameEnabled";

export function useRememberedLoginIdentifier() {
  const [initialPreference] = useState(readRememberedLoginPreference);
  const [identifier, setIdentifier] = useState(initialPreference.identifier);
  const [remember, setRememberState] = useState(initialPreference.remember);

  function setRemember(nextRemember: boolean) {
    setRememberState(nextRemember);
    writeRememberChoice(nextRemember);
    if (!nextRemember) removeRememberedIdentifier();
  }

  function persistRememberedIdentifier() {
    writeRememberChoice(remember);
    if (remember) writeRememberedIdentifier(identifier);
    else removeRememberedIdentifier();
  }

  return {
    identifier,
    persistRememberedIdentifier,
    remember,
    setIdentifier,
    setRemember,
  };
}

function readRememberedLoginPreference() {
  const remember = readRememberChoice();
  return {
    identifier: remember ? readRememberedIdentifier() : "",
    remember,
  };
}

function readRememberChoice() {
  try {
    return window.localStorage.getItem(rememberChoiceKey) !== "false";
  } catch {
    return true;
  }
}

function writeRememberChoice(remember: boolean) {
  try {
    window.localStorage.setItem(rememberChoiceKey, String(remember));
  } catch {
    // Remembering the choice is optional; login still works.
  }
}

function readRememberedIdentifier() {
  try {
    return (window.localStorage.getItem(identifierKey) ?? "").slice(0, 254);
  } catch {
    return "";
  }
}

function writeRememberedIdentifier(identifier: string) {
  const normalized = identifier.trim().slice(0, 254);
  if (!normalized) return removeRememberedIdentifier();
  try {
    window.localStorage.setItem(identifierKey, normalized);
  } catch {
    // Remembering the identifier is optional; login still works.
  }
}

function removeRememberedIdentifier() {
  try {
    window.localStorage.removeItem(identifierKey);
  } catch {
    // Storage is an enhancement; login still works.
  }
}
