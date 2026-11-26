import { useState } from "react";
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
  const [attempt, setAttempt] = useState<
    | { target: RecallTarget; mode: "camera"; stream: MediaStream | null }
    | { target: RecallTarget; mode: "ipad" }
    | null
  >(null);
  return (
    <div className="recall-launch">
      {camera.status === "active" ? (
        <button
          type="button"
          className="secondary-button"
          disabled={disabled}
          onClick={() => setAttempt({ target, mode: "camera", stream: camera.getStream() })}
        >
          {t("recall.title")}
        </button>
      ) : null}
      <button
        type="button"
        className="secondary-button"
        disabled={disabled}
        onClick={() => setAttempt({ target, mode: "ipad" })}
      >
        {t("recall.ipad")}
      </button>
      {attempt ? (
        <RecallDialog
          target={attempt.target}
          camera={
            attempt.mode === "camera"
              ? {
                  stream: attempt.stream,
                  capture: camera.capture,
                }
              : undefined
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
