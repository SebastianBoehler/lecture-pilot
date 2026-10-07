import { useState, type FormEvent, type ReactNode } from "react";

import { useCheckpointAnswer } from "./CheckpointDrafts";
import { CheckpointGuidance, useCheckpointExhausted } from "./CheckpointGuidance";
import { useI18n } from "./i18n";
import { MathText } from "./MathText";
import type { CanvasBlock } from "./types";

export function CheckpointSequence({
  block,
  className,
  highlightedText,
  sourceMarker,
  sectionId,
  onSubmitCheckpoint,
  secondaryAction,
  disabled,
}: {
  block: CanvasBlock;
  className: string;
  highlightedText: string | null;
  sourceMarker: ReactNode;
  sectionId?: string;
  onSubmitCheckpoint?: (gateId: string, sectionId: string, answer: string) => Promise<void>;
  secondaryAction?: ReactNode;
  disabled: boolean;
}) {
  const { t } = useI18n();
  const supportExhausted = useCheckpointExhausted(block.id);
  const effectiveDisabled = disabled || supportExhausted;
  const [pageDraft, setPageDraft] = useCheckpointAnswer(`${block.id}:${block.text}:sequence:page`);
  const [choiceDraft, setChoiceDraft] = useCheckpointAnswer(
    `${block.id}:${block.text}:sequence:choice`,
  );
  const choice =
    /^\d+$/.test(choiceDraft) && Number(choiceDraft) < block.items.length
      ? Number(choiceDraft)
      : null;
  const page = pageDraft === "1" && choice !== null ? 1 : 0;
  const [reason, setReason] = useCheckpointAnswer(`${block.id}:${block.text}:sequence:reason`);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const canAnswer = Boolean(onSubmitCheckpoint && sectionId && !effectiveDisabled);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (
      choice === null ||
      !reason.trim() ||
      !sectionId ||
      !onSubmitCheckpoint ||
      effectiveDisabled ||
      busy
    )
      return;
    setBusy(true);
    setError(null);
    try {
      await onSubmitCheckpoint(
        block.id,
        sectionId,
        `Selected option: ${block.items[choice]}\nReasoning: ${reason.trim()}`,
      );
      setChoiceDraft("");
      setReason("");
      setPageDraft("");
      setStatus(t("checkpoint.submitted"));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t("attempt.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className={`${className} canvas-checkpoint checkpoint-sequence`} id={block.id}>
      <div className="canvas-learning-label">{block.caption || t("checkpoint.label")}</div>
      <div className="checkpoint-sequence-heading">
        <span>{t("checkpoint.sequenceProgress", { current: String(page + 1) })}</span>
        <span>{page === 0 ? t("checkpoint.sequenceChoose") : t("checkpoint.sequenceExplain")}</span>
      </div>
      <div className="canvas-markdown">
        <MathText highlightedText={highlightedText} mode="block" text={block.text ?? ""} />
      </div>
      <CheckpointGuidance gateId={block.id} />
      {page === 0 ? (
        <div
          className="checkpoint-sequence-options"
          role="group"
          aria-label={t("checkpoint.sequenceChoose")}
        >
          {block.items.map((item, index) => (
            <button
              key={item}
              type="button"
              aria-pressed={choice === index}
              disabled={busy || !canAnswer}
              onClick={() => {
                setChoiceDraft(String(index));
                setStatus(null);
              }}
            >
              {String.fromCharCode(65 + index)}. {item}
            </button>
          ))}
          <button
            className="primary-button"
            type="button"
            disabled={choice === null || !canAnswer}
            onClick={() => setPageDraft("1")}
          >
            {t("checkpoint.sequenceNext")}
          </button>
          {!canAnswer ? sourceMarker : null}
        </div>
      ) : (
        <form className="canvas-checkpoint-form" onSubmit={submit}>
          <p className="checkpoint-sequence-choice">
            {t("checkpoint.sequenceYourChoice")}: {choice === null ? "" : block.items[choice]}
          </p>
          <label htmlFor={`${block.id}-reason`}>{t("checkpoint.sequenceReason")}</label>
          <textarea
            id={`${block.id}-reason`}
            value={reason}
            rows={4}
            required
            disabled={busy || !canAnswer}
            onChange={(event) => setReason(event.target.value)}
          />
          <div className="canvas-checkpoint-actions">
            <button className="secondary-button" type="button" onClick={() => setPageDraft("")}>
              {t("checkpoint.sequenceBack")}
            </button>
            <button
              className="primary-button"
              type="submit"
              disabled={busy || !canAnswer || !reason.trim()}
            >
              {t("checkpoint.submit")}
            </button>
            {secondaryAction}
            {sourceMarker}
          </div>
        </form>
      )}
      {status ? <p role="status">{status}</p> : null}
      {error ? (
        <p role="alert" className="form-error">
          {error}
        </p>
      ) : null}
    </aside>
  );
}
