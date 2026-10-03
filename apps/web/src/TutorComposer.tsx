import { ArrowUp } from "lucide-react";
import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { useI18n } from "./i18n";
import { useVersionUpdateActivity } from "./VersionUpdateBoundary";
import { SpeechInputControls } from "./SpeechInputControls";
import { useSpeechInput } from "./useSpeechInput";

export function TutorComposer({
  pending,
  onSendMessage,
}: {
  pending: boolean;
  onSendMessage: (message: string) => Promise<void>;
}) {
  const { t } = useI18n();
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const sendingRef = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const busy = pending || sending;
  const speech = useSpeechInput(busy, (text) => {
    setDraft((current) => `${current}${current && !/\s$/.test(current) ? " " : ""}${text}`);
    textareaRef.current?.focus();
  });
  const speechBusy = speech.state !== "idle";
  const displayedError = error ?? speech.error;
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
    if (!message || pending || sendingRef.current || speechBusy) return;
    sendingRef.current = true;
    setSending(true);
    setDraft("");
    setError(null);
    try {
      await onSendMessage(message);
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
      <form className="chat-form" onSubmit={submit}>
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
            <button
              aria-label={t("chat.send")}
              title={t("chat.send")}
              className="chat-send-button"
              disabled={busy || speechBusy || !draft.trim()}
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
