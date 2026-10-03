import { useCallback, useEffect, useRef, useState } from "react";
import { useI18n } from "./i18n";
import { startMicrophoneRecording } from "./speech/microphoneRecording";
import { WhistleClient } from "./speech/whistleClient";
import type { MicrophoneRecording, SpeechLanguage, SpeechState } from "./speech/whistleTypes";

export function useSpeechInput(disabled: boolean, onTranscript: (text: string) => void) {
  const { locale, t } = useI18n();
  const [language, setLanguage] = useState<SpeechLanguage>(locale);
  const [state, setState] = useState<SpeechState>("idle");
  const [error, setError] = useState<string | null>(null);
  const operation = useRef(0);
  const active = useRef(false);
  const client = useRef<WhistleClient | null>(null);
  const recording = useRef<MicrophoneRecording | null>(null);
  const context = useRef<AudioContext | null>(null);
  const captureAbort = useRef<AbortController | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const stopping = useRef(false);

  const release = useCallback(() => {
    operation.current++;
    active.current = false;
    clearTimeout(timer.current);
    captureAbort.current?.abort();
    captureAbort.current = null;
    recording.current?.cancel();
    recording.current = null;
    if (context.current?.state !== "closed") void context.current?.close();
    context.current = null;
    client.current?.dispose();
    client.current = null;
  }, []);

  useEffect(() => {
    function cancelHidden() {
      if (document.hidden && active.current) {
        release();
        setState("idle");
      }
    }
    document.addEventListener("visibilitychange", cancelHidden);
    return () => {
      document.removeEventListener("visibilitychange", cancelHidden);
      release();
    };
  }, [release]);

  useEffect(() => {
    if (disabled && active.current) {
      release();
      setState("idle");
    }
  }, [disabled, release]);

  function fail(cause: unknown) {
    const exception = cause instanceof Error || cause instanceof DOMException;
    const name = exception ? cause.name : "";
    const message = exception ? cause.message : "";
    if (name === "NotAllowedError" || name === "SecurityError") setError(t("speech.denied"));
    else if (name === "NotFoundError") setError(t("speech.noMicrophone"));
    else if (message === "unsupported") setError(t("speech.unsupported"));
    else if (message === "empty") setError(t("speech.empty"));
    else setError(`${t("speech.failed")}${message ? ` ${message}` : ""}`);
    release();
    setState("idle");
  }

  async function start() {
    if (disabled || active.current) return;
    const id = ++operation.current;
    active.current = true;
    stopping.current = false;
    setError(null);
    setState("loading");
    try {
      if (typeof AudioContext === "undefined") throw new Error("unsupported");
      // Resume within the click gesture, including on mobile Safari.
      const audio = new AudioContext();
      context.current = audio;
      const resumed = audio.resume();
      client.current ??= new WhistleClient();
      // Some browsers resume audio only after microphone permission is granted.
      // Do not let that promise prevent the permission request.
      void resumed.catch(() => undefined);
      await client.current.load();
      if (operation.current !== id) return;
      setState("requesting");
      const abort = new AbortController();
      captureAbort.current = abort;
      const microphone = await startMicrophoneRecording(audio, () => void stop(), abort.signal);
      if (operation.current !== id) {
        microphone.cancel();
        return;
      }
      recording.current = microphone;
      timer.current = setTimeout(() => fail(new Error(t("speech.audioFailed"))), 10_000);
      await resumed;
      if (operation.current !== id) return;
      clearTimeout(timer.current);
      setState("recording");
      timer.current = setTimeout(() => void stop(), 30_000);
    } catch (cause) {
      if (operation.current === id) fail(cause);
    }
  }

  async function stop() {
    const microphone = recording.current;
    if (!microphone || stopping.current) return;
    stopping.current = true;
    clearTimeout(timer.current);
    const id = operation.current;
    setState("transcribing");
    try {
      const pcm = await microphone.stop();
      if (operation.current !== id) return;
      recording.current = null;
      context.current = null;
      const text = await client.current!.transcribe(pcm, language);
      if (operation.current !== id) return;
      if (!text) throw new Error("empty");
      onTranscript(text);
      active.current = false;
      setState("idle");
    } catch (cause) {
      if (operation.current === id) fail(cause);
    }
  }

  function cancel() {
    release();
    setState("idle");
    setError(null);
  }

  return { language, setLanguage, state, error, start, stop, cancel };
}
