import { useRef, useState, type PointerEvent } from "react";
import { useVersionUpdateActivity } from "../shell/VersionUpdateBoundary";
import { useI18n } from "../i18n/i18n";

const WIDTH = 1200;
const HEIGHT = 900;
const PREFIX = "data:image/jpeg;base64,";

export function HandwritingPad({
  onSend,
  sendLabel,
}: {
  onSend: (image: string) => Promise<void>;
  sendLabel: "recall.feedback" | "recall.sendDesktop";
}) {
  const { t } = useI18n();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stroke = useRef<{ id: number; x: number; y: number } | null>(null);
  const sending = useRef(false);
  const [hasInk, setHasInk] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useVersionUpdateActivity(hasInk || busy);

  function draw(event: PointerEvent<HTMLCanvasElement>, first: boolean) {
    const previous = stroke.current;
    if (
      sending.current ||
      (first
        ? previous || event.button !== 0 || event.pointerType === "touch"
        : previous?.id !== event.pointerId)
    )
      return;
    const canvas = event.currentTarget;
    const context = canvas.getContext("2d", { alpha: false });
    if (!context) return;
    const bounds = canvas.getBoundingClientRect();
    const x = ((event.clientX - bounds.left) / bounds.width) * WIDTH;
    const y = ((event.clientY - bounds.top) / bounds.height) * HEIGHT;
    if (first) {
      canvas.setPointerCapture(event.pointerId);
      if (!hasInk) {
        context.fillStyle = "#fff";
        context.fillRect(0, 0, WIDTH, HEIGHT);
      }
      context.fillStyle = "#121212";
      context.beginPath();
      context.arc(x, y, 2, 0, 2 * Math.PI);
      context.fill();
      setHasInk(true);
    } else if (previous) {
      context.strokeStyle = "#121212";
      context.lineWidth = 3 + (event.pointerType === "pen" ? event.pressure * 3 : 1);
      context.lineCap = "round";
      context.beginPath();
      context.moveTo(previous.x, previous.y);
      context.lineTo(x, y);
      context.stroke();
    }
    stroke.current = { id: event.pointerId, x, y };
  }

  function end(event: PointerEvent<HTMLCanvasElement>) {
    if (stroke.current?.id === event.pointerId) stroke.current = null;
  }

  function clear() {
    const context = canvasRef.current?.getContext("2d", { alpha: false });
    if (context) {
      context.fillStyle = "#fff";
      context.fillRect(0, 0, WIDTH, HEIGHT);
    }
    setHasInk(false);
    setError(null);
  }

  async function send() {
    if (sending.current || !hasInk || stroke.current) return;
    sending.current = true;
    setBusy(true);
    setError(null);
    try {
      const data = canvasRef.current?.toDataURL("image/jpeg", 0.82);
      if (!data?.startsWith(PREFIX) || data.length - PREFIX.length > 640_000) {
        throw new Error(t("recall.inkExportFailed"));
      }
      await onSend(data.slice(PREFIX.length));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("recall.pairFailed"));
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }

  return (
    <>
      <canvas
        ref={canvasRef}
        className="recall-ink"
        width={WIDTH}
        height={HEIGHT}
        aria-label={t("recall.pad")}
        onPointerDown={(event) => draw(event, true)}
        onPointerMove={(event) => draw(event, false)}
        onPointerUp={end}
        onPointerCancel={end}
        onLostPointerCapture={end}
      />
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
      <div className="recall-actions">
        <button
          type="button"
          className="secondary-button"
          disabled={!hasInk || busy}
          onClick={clear}
        >
          {t("recall.clear")}
        </button>
        <button
          type="button"
          className="primary-button"
          disabled={!hasInk || busy}
          onClick={() => void send()}
        >
          {t(busy ? "recall.sending" : sendLabel)}
        </button>
      </div>
    </>
  );
}
