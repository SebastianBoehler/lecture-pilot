import { useEffect, useState } from "react";

import { errorMessage } from "../shared/errorMessage";
import type { LoginSession } from "../shared/types";
import {
  getCanvasChangeOptions,
  requestCanvasChange,
  type CanvasChangeOptions,
} from "./canvasChangeRequestApi";

export const MAX_CHANGE_INSTRUCTION = 2000;

/** Loads the lecture's sections and submits one change request; errors keep the backend detail. */
export function useCanvasChangeRequest(input: {
  courseId: string;
  lectureId: string;
  session: LoginSession;
  onSubmitted: () => void;
}) {
  const { courseId, lectureId, session, onSubmitted } = input;
  const [options, setOptions] = useState<CanvasChangeOptions | null>(null);
  const [unavailable, setUnavailable] = useState<string | null>(null);
  const [instruction, setInstruction] = useState("");
  const [sectionIds, setSectionIds] = useState<readonly string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getCanvasChangeOptions(courseId, lectureId, session).then(
      (loaded) => {
        if (active) setOptions(loaded);
      },
      (cause: unknown) => {
        if (active) setUnavailable(errorMessage(cause, "The lecture cannot be changed now."));
      },
    );
    return () => {
      active = false;
    };
  }, [courseId, lectureId, session]);

  const trimmed = instruction.trim();
  const canSubmit =
    Boolean(options) &&
    !submitting &&
    trimmed.length > 0 &&
    trimmed.length <= MAX_CHANGE_INSTRUCTION;

  async function submit() {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      await requestCanvasChange(
        courseId,
        lectureId,
        { instruction: trimmed, section_ids: sectionIds },
        session,
      );
      onSubmitted();
    } catch (cause) {
      setError(errorMessage(cause, "The change could not be requested."));
      setSubmitting(false);
    }
  }

  function toggleSection(id: string) {
    setSectionIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );
  }

  return {
    options,
    unavailable,
    instruction,
    setInstruction,
    sectionIds,
    toggleSection,
    submitting,
    error,
    canSubmit,
    submit,
  };
}
