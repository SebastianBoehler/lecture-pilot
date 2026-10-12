import { useRef, useState } from "react";
import { CheckpointBlock } from "./CanvasLearningBlocks";
import { useI18n } from "./i18n";
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
  const { t } = useI18n();
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
  if (!check || !section) return <p role="alert">{t("focused.taskChanged")}</p>;
  return (
    <section className="focused-checkpoint" aria-label={t("focused.label")}>
      {state.active_session_goal ? (
        <p>
          <strong>{t("focused.goal")}</strong> {state.active_session_goal}
        </p>
      ) : null}
      <h2>
        {t(check.stage === "delayed_transfer" ? "focused.laterReview" : "focused.tryIndependently")}
      </h2>
      <p>{t("focused.closedNotice")}</p>
      <CheckpointBlock
        key={`${check.task_id}:${check.issued_at}`}
        block={{
          id: check.gate_id,
          type: "checkpoint",
          text: check.prompt,
          items: [],
          caption: t("focused.yourAttempt"),
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
            {busy ? t("focused.recordingHelp") : t("focused.requestHelp")}
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
