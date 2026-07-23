import { useCallback, useEffect, useRef, useState } from "react";

import { isStudentAccount } from "./authz";
import type { LoginSession } from "./types";

export const FEEDBACK_TURN_THRESHOLD = 5;
const FEEDBACK_PROMPT_VERSION = "v1";

export type FeedbackPromptSource = "manual" | "threshold";

type FeedbackPromptState = {
  prompted: boolean;
  qualifiedVisitId?: string;
  successfulTurns: number;
};

export function useFeedbackPrompt(session: LoginSession | null, homeVisible = false) {
  const [source, setSource] = useState<FeedbackPromptSource | null>(null);
  const visitId = useRef(globalThis.crypto.randomUUID());

  useEffect(() => setSource(null), [session?.username]);

  useEffect(() => {
    if (!homeVisible || !isEligibleStudent(session)) return;
    const key = feedbackPromptStorageKey(session.username);
    const current = readPromptState(key);
    if (
      current.prompted ||
      current.successfulTurns < FEEDBACK_TURN_THRESHOLD ||
      current.qualifiedVisitId === visitId.current
    ) {
      return;
    }
    writePromptState(key, { ...current, prompted: true });
    setSource("threshold");
  }, [homeVisible, session]);

  const recordSuccessfulTutorTurn = useCallback(() => {
    if (!isEligibleStudent(session)) return;
    const key = feedbackPromptStorageKey(session.username);
    const current = readPromptState(key);
    if (current.prompted) return;
    const successfulTurns = current.successfulTurns + 1;
    writePromptState(key, {
      prompted: false,
      qualifiedVisitId:
        successfulTurns >= FEEDBACK_TURN_THRESHOLD
          ? (current.qualifiedVisitId ?? visitId.current)
          : current.qualifiedVisitId,
      successfulTurns,
    });
  }, [session]);

  const openManually = useCallback(() => {
    if (session) setSource("manual");
  }, [session]);

  const close = useCallback(() => setSource(null), []);
  return { close, openManually, recordSuccessfulTutorTurn, source };
}

export function feedbackPromptStorageKey(username: string) {
  return `lecturepilot.feedback-prompt.${FEEDBACK_PROMPT_VERSION}.${username}`;
}

function isEligibleStudent(session: LoginSession | null): session is LoginSession {
  return Boolean(session && isStudentAccount(session) && session.auth_transport !== "dev_headers");
}

function readPromptState(key: string): FeedbackPromptState {
  const raw = window.localStorage.getItem(key);
  if (!raw) return { prompted: false, successfulTurns: 0 };
  try {
    const parsed = JSON.parse(raw) as Partial<FeedbackPromptState>;
    return {
      prompted: parsed.prompted === true,
      qualifiedVisitId:
        typeof parsed.qualifiedVisitId === "string" ? parsed.qualifiedVisitId : undefined,
      successfulTurns:
        typeof parsed.successfulTurns === "number" && parsed.successfulTurns >= 0
          ? parsed.successfulTurns
          : 0,
    };
  } catch {
    return { prompted: false, successfulTurns: 0 };
  }
}

function writePromptState(key: string, state: FeedbackPromptState) {
  window.localStorage.setItem(key, JSON.stringify(state));
}
