import type { TutorMessageOptions } from "../canvas/canvasLearningActions";
import { TutorCameraButton, TutorCameraPreview } from "./TutorCamera";
import { RecallLauncher } from "./RecallLauncher";
import type { RecallTarget } from "./recallTarget";
import { useTutorCamera } from "./useTutorCamera";
import { ArrowUp } from "lucide-react";
import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { useI18n } from "../i18n/i18n";
import { useVersionUpdateActivity } from "../shell/VersionUpdateBoundary";
import { SpeechInputControls } from "./SpeechInputControls";
import { useSpeechInput } from "./useSpeechInput";

export function TutorComposer({
  pending,
  recallTarget,
  onRecallSaved,
  onSendMessage,
}: {
  pending: boolean;
  recallTarget?: RecallTarget;
  onRecallSaved?: () => void;
  onSendMessage: (message: string, options?: TutorMessageOptions) => Promise<string | void>;
}) {
  const { t } = useI18n();
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const sendingRef = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const busy = pending || sending;
  const camera = useTutorCamera();
  const speech = useSpeechInput(busy, (text) => {
    setDraft((current) => `${current}${current && !/\s$/.test(current) ? " " : ""}${text}`);
    textareaRef.current?.focus();
  });
  const speechBusy = speech.state !== "idle";
  const displayedError = error ?? speech.error ?? camera.error;
  useVersionUpdateActivity(busy || speechBusy || Boolean(draft.trim()));
  useLayoutEffect(() => {
    const field = textareaRef.current;
    if (!field) return;
    field.style.height = "auto";
    field.style.height = `${Math.min(field.scrollHeight, 180)}px`;
  }, [draft]);
  useEffect(() => {
    if (displayedError) textareaRef.current?.focus();
  }, [displayedError]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || pending || sendingRef.current || speechBusy || camera.status === "opening")
      return;
    sendingRef.current = true;
    setSending(true);
    setDraft("");
    setError(null);
    try {
      const cameraFrame = camera.capture();
      if (cameraFrame) await onSendMessage(message, { cameraFrame });
      else await onSendMessage(message);
    } catch (cause) {
      setDraft(message);
      setError(cause instanceof Error ? cause.message : t("chat.failed"));
    } finally {
      sendingRef.current = false;
      setSending(false);
    }
  }

  function keyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (
      event.key !== "Enter" ||
      event.shiftKey ||
      event.nativeEvent.isComposing ||
      event.keyCode === 229
    )
      return;
    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  }

  return (
    <div className="chat-dock">
      {recallTarget ? (
        <RecallLauncher
          target={recallTarget}
          camera={camera}
          disabled={busy || speechBusy}
          onSend={onSendMessage}
          onSaved={onRecallSaved}
        />
      ) : null}
      <form className="chat-form" onSubmit={submit}>
        <TutorCameraPreview
          status={camera.status}
          devices={camera.devices}
          selected={camera.selected}
          start={camera.start}
          setPreview={camera.setPreview}
        />
        <div className="chat-composer">
          <textarea
            aria-label={t("chat.message")}
            id="tutor-message"
            ref={textareaRef}
            disabled={busy}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={keyDown}
            aria-describedby={displayedError ? "tutor-error" : "tutor-keyboard tutor-speech"}
            placeholder={t("chat.placeholder")}
            rows={2}
          />
          <div className="chat-composer-actions">
            <span id="tutor-keyboard" className="visually-hidden">
              {t("chat.keyboard")}
            </span>
            <SpeechInputControls
              disabled={busy}
              language={speech.language}
              onLanguage={speech.setLanguage}
              state={speech.state}
              onStart={speech.start}
              onStop={speech.stop}
              onCancel={speech.cancel}
            />
            <TutorCameraButton camera={camera} disabled={busy} />
            <button
              aria-label={t("chat.send")}
              title={t("chat.send")}
              className="chat-send-button"
              disabled={busy || speechBusy || camera.status === "opening" || !draft.trim()}
              type="submit"
            >
              <ArrowUp size={18} aria-hidden="true" />
            </button>
          </div>
        </div>
      </form>
      <p id="tutor-speech" className="chat-speech-status" role={speechBusy ? "status" : undefined}>
        {t(speech.state === "idle" ? "speech.privacy" : `speech.${speech.state}`)}
      </p>
      {displayedError ? (
        <p id="tutor-error" className="form-error" role="alert">
          {displayedError}
        </p>
      ) : null}
    </div>
  );
}
