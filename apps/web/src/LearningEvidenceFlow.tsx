import { useRef, useState } from "react";
import { CheckpointBlock } from "./CanvasLearningBlocks";
import { MathText } from "./MathText";
import type { LearnerLessonState } from "./learnerLessonStateTypes";
import type { CanvasDocument } from "./types";

export function LearningEvidenceFlow({
  state,
  document,
}: {
  state: LearnerLessonState | null;
  document: CanvasDocument;
}) {
  if (!state?.pending_check && !state?.goal_evidence?.length) return null;
  return (
    <section className="learning-evidence-flow" aria-label="Learning evidence">
      {state.active_session_goal ? (
        <p>
          <strong>Goal:</strong> {state.active_session_goal}
        </p>
      ) : null}
      <p>Attempt → targeted support → a fresh independent task → later review</p>
      {state.goal_evidence?.map((evidence) => (
        <div key={evidence.gate_id}>
          <p>
            <strong>
              {document.sections
                .flatMap((section) => section.blocks)
                .find((block) => block.id === evidence.gate_id)?.caption ?? "Learning goal"}
            </strong>
            {": "}
            {evidence.delayed
              ? "Demonstrated again after a delay"
              : evidence.independent
                ? "Demonstrated independently in this app"
                : evidence.supported
                  ? "Demonstrated with support · independent check still needed"
                  : "Evidence still needed"}
          </p>
          {!state.pending_check?.focus_required && evidence.missing_evidence?.length ? (
            <ul aria-label="Evidence to demonstrate">
              {evidence.missing_evidence.map((text, index) => (
                <li key={index}>{text}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ))}
      {state.pending_check?.bank_exhausted ? (
        <p role="status">
          All reviewed variants have been used. You can continue with support; a new reviewed task
          is needed for independent evidence.
        </p>
      ) : null}
      {!state.pending_check?.focus_required && state.pending_check?.assistance_content ? (
        <div className="canvas-markdown">
          <MathText
            highlightedText={null}
            mode="block"
            text={state.pending_check.assistance_content}
          />
        </div>
      ) : null}
      {state.due_gate_reviews.length ? <p>A later review is ready in your learning path.</p> : null}
    </section>
  );
}

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
        onSubmitCheckpoint={busy ? undefined : submit}
      />
      <button
        type="button"
        className="refresh-button"
        disabled={busy || submitting}
        onClick={() => void help()}
      >
        {busy ? "Recording help…" : "Request help and open materials"}
      </button>
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
