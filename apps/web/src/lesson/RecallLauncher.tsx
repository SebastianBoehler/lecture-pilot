import { useId, useState } from "react";
import { useI18n } from "../i18n/i18n";
import type { TutorMessageOptions } from "../canvas/canvasLearningActions";
import { RecallDialog } from "./RecallDialog";
import type { RecallTarget } from "./recallTarget";
import type { useTutorCamera } from "./useTutorCamera";

export function RecallLauncher({
  target,
  camera,
  disabled,
  onSend,
  onSaved,
}: {
  target: RecallTarget;
  camera: ReturnType<typeof useTutorCamera>;
  disabled: boolean;
  onSaved?: () => void;
  onSend: (message: string, options?: TutorMessageOptions) => Promise<string | void>;
}) {
  const { t } = useI18n();
  const sectionLabel = useId();
  const [attempt, setAttempt] = useState<
    | { target: RecallTarget; mode: "camera"; stream: MediaStream | null }
    | { target: RecallTarget; mode: "local" | "paired" }
    | null
  >(null);
  return (
    <div className="recall-launch">
      <p className="recall-launch-section" id={sectionLabel}>
        {t("recall.sectionLabel", { title: target.title })}
      </p>
      <button
        type="button"
        className="secondary-button"
        aria-describedby={sectionLabel}
        disabled={disabled}
        onClick={() => setAttempt({ target, mode: "local" })}
      >
        {t("recall.writeHere")}
      </button>
      {camera.status === "active" ? (
        <button
          type="button"
          className="secondary-button"
          aria-describedby={sectionLabel}
          disabled={disabled}
          onClick={() => setAttempt({ target, mode: "camera", stream: camera.getStream() })}
        >
          {t("recall.title")}
        </button>
      ) : null}
      <button
        type="button"
        className="secondary-button"
        aria-describedby={sectionLabel}
        disabled={disabled}
        onClick={() => setAttempt({ target, mode: "paired" })}
      >
        {t("recall.ipad")}
      </button>
      {attempt ? (
        <RecallDialog
          target={attempt.target}
          input={
            attempt.mode === "camera"
              ? {
                  mode: "camera",
                  stream: attempt.stream,
                  capture: camera.capture,
                }
              : { mode: attempt.mode }
          }
          onClose={() => setAttempt(null)}
          onSaved={onSaved}
          onSubmit={(cameraFrame) =>
            onSend(t("recall.message"), {
              cameraFrame,
              focusedSectionId: attempt.target.sectionId,
              recallPublicationVersion: attempt.target.publicationVersion,
            })
          }
        />
      ) : null}
    </div>
  );
}
