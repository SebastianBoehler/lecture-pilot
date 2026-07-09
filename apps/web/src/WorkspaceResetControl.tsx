import { RotateCcw } from "lucide-react";
import type { FormEvent } from "react";
import { useState } from "react";

import { useI18n } from "./i18n";
import type { LearnerWorkspaceResetOptions } from "./learnerWorkspaceApi";

export type WorkspaceResetSelection = Omit<LearnerWorkspaceResetOptions, "user_id">;

export function WorkspaceResetControl({
  disabled = false,
  onReset,
}: {
  disabled?: boolean;
  onReset: (options: WorkspaceResetSelection) => Promise<void>;
}) {
  const { t } = useI18n();
  const [resetCanvas, setResetCanvas] = useState(true);
  const [resetCourseMemory, setResetCourseMemory] = useState(true);
  const [resetProgress, setResetProgress] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setStatus(null);
    if (!resetCanvas && !resetCourseMemory && !resetProgress) {
      setError(t("reset.selectScope"));
      return;
    }
    if (!window.confirm(t("reset.confirm"))) {
      return;
    }
    setBusy(true);
    try {
      await onReset({
        reset_canvas: resetCanvas,
        reset_course_memory: resetCourseMemory,
        reset_progress: resetProgress,
      });
      setStatus(t("reset.done"));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : t("reset.failed"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="workspace-reset-menu">
      <summary aria-disabled={disabled}>
        <RotateCcw size={15} />
        {t("reset.title")}
      </summary>
      <form className="workspace-reset-form" onSubmit={handleSubmit}>
        <label>
          <input
            checked={resetCanvas}
            disabled={disabled || busy}
            type="checkbox"
            onChange={(event) => setResetCanvas(event.target.checked)}
          />
          {t("reset.generatedCanvas")}
        </label>
        <label>
          <input
            checked={resetCourseMemory}
            disabled={disabled || busy}
            type="checkbox"
            onChange={(event) => setResetCourseMemory(event.target.checked)}
          />
          {t("reset.courseMemory")}
        </label>
        <label>
          <input
            checked={resetProgress}
            disabled={disabled || busy}
            type="checkbox"
            onChange={(event) => setResetProgress(event.target.checked)}
          />
          {t("reset.progress")}
        </label>
        <button className="primary-button" disabled={disabled || busy} type="submit">
          {busy ? t("reset.submitting") : t("reset.submit")}
        </button>
        {error ? <p className="form-error">{error}</p> : null}
        {status ? <p className="form-status">{status}</p> : null}
      </form>
    </details>
  );
}
