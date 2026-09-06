import { useRef, useState } from "react";
import { CheckpointBlock } from "./CanvasLearningBlocks";
import type { LearnerLessonState } from "./learnerLessonStateTypes";
import type { CanvasDocument } from "./types";

export function FocusedCheckpoint({
  state,
  document,
  onSubmit,
  onHelp,
  busy,
  error,
}: {
  state: LearnerLessonState;
  document: CanvasDocument;
  onSubmit: (gateId: string, sectionId: string, answer: string) => Promise<void>;
  onHelp: () => Promise<void>;
  busy: boolean;
  error: string | null;
}) {
  const actionInFlight = useRef(false);
  const [submitting, setSubmitting] = useState(false);
  async function submit(gateId: string, sectionId: string, answer: string) {
    if (actionInFlight.current || busy) return;
    actionInFlight.current = true;
    setSubmitting(true);
    try {
      await onSubmit(gateId, sectionId, answer);
    } finally {
      actionInFlight.current = false;
      setSubmitting(false);
    }
  }
  async function help() {
    if (actionInFlight.current || busy) return;
    actionInFlight.current = true;
    try {
      await onHelp();
    } finally {
      actionInFlight.current = false;
    }
  }
  const check = state.pending_check;
  const section = document.sections.find((item) =>
    item.blocks.some((block) => block.id === check?.gate_id),
  );
  if (!check || !section)
    return <p role="alert">The task no longer matches this canvas. Reload the lecture.</p>;
  return (
    <section className="focused-checkpoint" aria-label="Independent attempt">
      {state.active_session_goal ? (
        <p>
          <strong>Goal:</strong> {state.active_session_goal}
        </p>
      ) : null}
      <h2>{check.stage === "delayed_transfer" ? "Later review" : "Try independently"}</h2>
      <p>
        Teaching, notes, sources and chat are closed during this attempt. Request help to reopen
        them; this attempt will then be recorded as supported.
      </p>
      <CheckpointBlock
        key={`${check.task_id}:${check.issued_at}`}
        block={{
          id: check.gate_id,
          type: "checkpoint",
          text: check.prompt,
          items: [],
          caption: "Your attempt",
        }}
        className="canvas-block"
        highlightedText={null}
        sourceMarker={null}
        sectionId={section.id}
        onSubmitCheckpoint={submit}
        disabled={busy}
        secondaryAction={
          <button
            type="button"
            className="checkpoint-help"
            disabled={busy || submitting}
            onClick={() => void help()}
          >
            {busy ? "Recording help…" : "Request help and open materials"}
          </button>
        }
      />
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
