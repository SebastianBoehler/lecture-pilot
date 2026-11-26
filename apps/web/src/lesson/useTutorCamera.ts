import { useCallback, useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n/i18n";

const MAX_FRAME_EDGE = 1600;
const MAX_BASE64_LENGTH = 640_000;
const JPEG_PREFIX = "data:image/jpeg;base64,";

export function useTutorCamera() {
  const { t } = useI18n();
  const video = useRef<HTMLVideoElement | null>(null);
  const setPreview = useCallback((element: HTMLVideoElement | null) => {
    video.current = element;
  }, []);
  const stream = useRef<MediaStream | null>(null);
  const requestId = useRef(0);
  const [status, setStatus] = useState<"off" | "opening" | "active">("off");
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState<string | null>(null);

  const release = useCallback(() => {
    requestId.current += 1;
    const current = stream.current;
    stream.current = null;
    current?.getTracks().forEach((track) => track.stop());
    if (video.current) video.current.srcObject = null;
  }, []);

  useEffect(() => release, [release]);

  function stop() {
    release();
    setStatus("off");
    setError(null);
  }

  async function start(deviceId: string = "") {
    release();
    setError(null);
    const media = navigator.mediaDevices;
    if (!media?.getUserMedia || !media.enumerateDevices) {
      setStatus("off");
      setError(t("camera.unsupported"));
      return;
    }

    const id = requestId.current;
    setStatus("opening");
    try {
      const next = await media.getUserMedia({
        audio: false,
        video: {
          deviceId: deviceId ? { exact: deviceId } : undefined,
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      });
      if (id !== requestId.current) {
        next.getTracks().forEach((track) => track.stop());
        return;
      }
      stream.current = next;
      const track = next.getVideoTracks()[0];
      if (!track || !video.current) throw new Error();
      track.addEventListener(
        "ended",
        () => {
          if (stream.current !== next) return;
          stop();
          setError(t("camera.disconnected"));
        },
        { once: true },
      );

      const available = (await media.enumerateDevices()).filter(
        ({ kind }) => kind === "videoinput",
      );
      if (id !== requestId.current) return;
      if (track.readyState !== "live" || !video.current) throw new Error();
      setDevices(available);
      setSelected(track.getSettings().deviceId ?? deviceId);
      video.current.srcObject = next;
      setStatus("active");
    } catch (cause) {
      if (id !== requestId.current) return;
      stop();
      setError(
        t(
          cause instanceof DOMException && cause.name === "NotAllowedError"
            ? "camera.denied"
            : "camera.failed",
        ),
      );
    }
  }

  function capture() {
    if (status === "off") return undefined;
    const preview = video.current;
    const track = stream.current?.getVideoTracks()[0];
    if (
      !preview ||
      !track ||
      track.readyState !== "live" ||
      track.muted ||
      preview.readyState < HTMLMediaElement.HAVE_CURRENT_DATA ||
      !preview.videoWidth ||
      !preview.videoHeight
    ) {
      throw new Error(t("camera.frameUnavailable"));
    }
    const scale = Math.min(1, MAX_FRAME_EDGE / Math.max(preview.videoWidth, preview.videoHeight));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(preview.videoWidth * scale));
    canvas.height = Math.max(1, Math.round(preview.videoHeight * scale));
    const context = canvas.getContext("2d");
    if (!context) throw new Error(t("camera.frameUnavailable"));
    context.drawImage(preview, 0, 0, canvas.width, canvas.height);
    const data = canvas.toDataURL("image/jpeg", 0.82);
    if (!data.startsWith(JPEG_PREFIX)) throw new Error(t("camera.frameUnavailable"));
    const frame = data.slice(JPEG_PREFIX.length);
    if (frame.length > MAX_BASE64_LENGTH) throw new Error(t("camera.frameTooLarge"));
    return frame;
  }

  return {
    setPreview,
    status,
    devices,
    selected,
    error,
    start,
    stop,
    capture,
    getStream: () => stream.current,
  };
}
