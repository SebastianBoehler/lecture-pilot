import { Mic, Square, X } from "lucide-react";
import { useI18n } from "./i18n";
import type { SpeechLanguage, SpeechState } from "./speech/whistleTypes";

export function SpeechInputControls({
  disabled,
  language,
  onLanguage,
  state,
  onStart,
  onStop,
  onCancel,
}: {
  disabled: boolean;
  language: SpeechLanguage;
  onLanguage(language: SpeechLanguage): void;
  state: SpeechState;
  onStart(): Promise<void>;
  onStop(): Promise<void>;
  onCancel(): void;
}) {
  const { t } = useI18n();
  const recording = state === "recording";
  const waiting = state !== "idle" && !recording;
  const label = t(waiting ? "speech.cancel" : recording ? "speech.stop" : "speech.start");
  return (
    <>
      <select
        aria-label={t("speech.language")}
        title={t("speech.language")}
        className="chat-speech-language"
        value={language}
        disabled={disabled || state !== "idle"}
        onChange={(event) => onLanguage(event.target.value as SpeechLanguage)}
      >
        <option value="en">EN</option>
        <option value="de">DE</option>
      </select>
      <button
        type="button"
        className={`chat-speech-button${recording ? " is-recording" : ""}`}
        aria-label={label}
        aria-pressed={recording}
        title={label}
        disabled={disabled}
        onClick={() => (waiting ? onCancel() : void (recording ? onStop() : onStart()))}
      >
        {waiting ? (
          <X size={18} aria-hidden="true" />
        ) : recording ? (
          <Square size={16} aria-hidden="true" />
        ) : (
          <Mic size={18} aria-hidden="true" />
        )}
      </button>
    </>
  );
}
