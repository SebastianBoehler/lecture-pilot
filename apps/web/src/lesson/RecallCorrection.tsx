import { useRef, useState } from "react";
import { MathText } from "../canvas/MathText";
import { useI18n } from "../i18n/i18n";
import { apiRequest } from "../shared/apiRequest";
import type { RecallTarget } from "./recallTarget";

export function RecallCorrection({
  target,
  feedback,
  onSaved,
  onClose,
}: {
  target: RecallTarget;
  feedback: string;
  onSaved?: () => void;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState<string | null>(null);
  const noteId = useRef<string | null>(null);

  async function save() {
    if (!target.blockId || !note.trim() || status !== "idle") return;
    setStatus("saving");
    setError(null);
    const failure = t("recall.saveFailed");
    try {
      noteId.current ??= crypto.randomUUID();
      await apiRequest(
        target.session,
        `/courses/${encodeURIComponent(target.courseId)}/lectures/${encodeURIComponent(target.lectureId)}/annotations/${noteId.current}`,
        failure,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            publication_version: target.publicationVersion,
            block_id: target.blockId,
            comment: note.trim(),
          }),
        },
      );
      setStatus("saved");
      onSaved?.();
    } catch (cause) {
      setStatus("idle");
      setError(cause instanceof Error ? cause.message : failure);
    }
  }

  return (
    <>
      <MathText text={feedback} mode="block" highlightedText={null} allowLinks={false} />
      {target.blockId && status !== "saved" ? (
        <label className="recall-note">
          {t("recall.correction")}
          <textarea
            rows={3}
            maxLength={2000}
            disabled={status === "saving"}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </label>
      ) : null}
      {status === "saved" ? <p role="status">{t("recall.saved")}</p> : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="recall-actions">
        <button
          type="button"
          className="secondary-button"
          disabled={status === "saving"}
          onClick={onClose}
        >
          {t("recall.back")}
        </button>
        {target.blockId && status !== "saved" ? (
          <button
            type="button"
            className="primary-button"
            disabled={status !== "idle" || !note.trim()}
            onClick={() => void save()}
          >
            {t("recall.save")}
          </button>
        ) : null}
      </div>
    </>
  );
}
