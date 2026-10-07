import { Mic, Square, X } from "lucide-react";
import { useEffect, useId, useState } from "react";
import { useI18n } from "./i18n";
import type { SpeechLanguage, SpeechState } from "./speech/whistleTypes";

const MAX_RECORDING_SECONDS = 30;
const LANGUAGES: { value: SpeechLanguage; short: string; name: string }[] = [
  { value: "en", short: "EN", name: "English" },
  { value: "de", short: "DE", name: "Deutsch" },
];

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
  const name = useId();
  const recording = state === "recording";
  const waiting = state !== "idle" && !recording;
  const elapsed = useElapsedSeconds(recording);
  const label = t(waiting ? "speech.cancel" : recording ? "speech.stop" : "speech.start");
  const stateClass = recording ? " is-recording" : waiting ? " is-waiting" : "";
  return (
    <div className="chat-speech">
      <div
        className="chat-speech-language"
        role="radiogroup"
        aria-label={t("speech.language")}
        title={t("speech.language")}
      >
        {LANGUAGES.map((option) => (
          <label key={option.value}>
            <input
              type="radio"
              name={name}
              value={option.value}
              aria-label={option.name}
              checked={language === option.value}
              disabled={disabled || state !== "idle"}
              onChange={() => onLanguage(option.value)}
            />
            <span aria-hidden="true">{option.short}</span>
          </label>
        ))}
      </div>
      <button
        type="button"
        className={`chat-speech-button${stateClass}`}
        aria-label={label}
        aria-pressed={recording}
        title={label}
        disabled={disabled}
        onClick={() => (waiting ? onCancel() : void (recording ? onStop() : onStart()))}
      >
        {waiting ? (
          <X size={16} aria-hidden="true" />
        ) : recording ? (
          <Square size={12} fill="currentColor" aria-hidden="true" />
        ) : (
          <Mic size={17} aria-hidden="true" />
        )}
      </button>
      {recording ? (
        <span className="chat-speech-timer" aria-hidden="true">
          {formatSeconds(elapsed)} / {formatSeconds(MAX_RECORDING_SECONDS)}
        </span>
      ) : null}
    </div>
  );
}

function useElapsedSeconds(active: boolean) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!active) return undefined;
    const startedAt = Date.now();
    setElapsed(0);
    const interval = window.setInterval(
      () =>
        setElapsed(Math.min(MAX_RECORDING_SECONDS, Math.floor((Date.now() - startedAt) / 1000))),
      250,
    );
    return () => window.clearInterval(interval);
  }, [active]);
  return active ? elapsed : 0;
}

function formatSeconds(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
