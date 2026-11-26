import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import QRCode from "qrcode";
import { useI18n } from "../i18n/i18n";
import { useVersionUpdateActivity } from "../shell/VersionUpdateBoundary";
import { lessonPath } from "../shell/appRoute";
import { useModalDialog } from "../shared/useModalDialog";
import { pollUntil } from "../shared/polling";
import { RecallCorrection } from "./RecallCorrection";
import type { RecallTarget } from "./recallTarget";
import { HandwritingPad } from "./HandwritingPad";
import { inkPairRequest, type InkLecture } from "./inkPairingApi";
import "./recall.css";

function Modal({
  title,
  children,
  onClose,
  wide,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const id = useId();
  const ref = useModalDialog();
  return createPortal(
    <dialog
      ref={ref}
      aria-labelledby={id}
      className={`recall-dialog${wide ? " recall-dialog-wide" : ""}`}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onKeyDown={(event) => event.stopPropagation()}
    >
      <h2 id={id}>{title}</h2>
      {children}
    </dialog>,
    document.body,
  );
}

export function RecallDialog({
  target,
  input,
  onSubmit,
  onSaved,
  onClose,
}: {
  target: RecallTarget;
  input:
    | { mode: "camera"; stream: MediaProvider | null; capture: () => string | undefined }
    | { mode: "local" | "paired" };
  onSubmit: (image: string) => Promise<string | void>;
  onSaved?: () => void;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const [pairUrl, setPairUrl] = useState<string | null>(null);
  const [qr, setQr] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ message: string; image: string } | null>(null);
  const [ink, setInk] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const sending = useRef(false);
  const { mode } = input;
  const fallback = t("recall.pairFailed");
  useVersionUpdateActivity(true);

  useEffect(() => {
    if (mode !== "paired") return;
    const controller = new AbortController();
    let code: string | undefined;
    const closePair = () => {
      if (code) void inkPairRequest(target, "DELETE", fallback, { code }).catch(() => undefined);
    };
    async function pair() {
      try {
        const result = await inkPairRequest<{ code: string; expires_in: number }>(
          target,
          "POST",
          fallback,
        );
        code = result.code;
        if (controller.signal.aborted) return;
        const url = new URL(lessonPath(target.courseId, target.lectureId), window.location.origin);
        url.hash = `ink=${code}`;
        const qrImage = await QRCode.toDataURL(url.href, { width: 210, margin: 2 });
        if (controller.signal.aborted) return;
        setPairUrl(url.href);
        setQr(qrImage);
        const image = await pollUntil<string>({
          signal: controller.signal,
          initialDelayMs: 1000,
          maxDelayMs: 4000,
          timeoutMs: result.expires_in * 1000,
          poll: async (signal) => {
            const page = await inkPairRequest<{ image: string | null }>(target, "GET", fallback, {
              code,
              signal,
            });
            return page.image ? { done: true, value: page.image } : { done: false };
          },
        });
        if (!controller.signal.aborted) setInk(image);
      } catch (cause) {
        if (!controller.signal.aborted) {
          setError(cause instanceof Error ? cause.message : fallback);
        }
      } finally {
        closePair();
      }
    }
    void pair();
    return () => controller.abort();
  }, [mode, fallback, target]);

  async function submit(localImage?: string) {
    if (sending.current) return;
    sending.current = true;
    setBusy(true);
    setError(null);
    try {
      const image = input.mode === "camera" ? input.capture() : (localImage ?? ink);
      if (!image) throw new Error(t("recall.imageRequired"));
      const reply = await onSubmit(image);
      if (reply) setFeedback({ message: reply, image });
      else onClose();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("chat.failed"));
    } finally {
      sending.current = false;
      setBusy(false);
    }
  }

  return (
    <Modal
      title={t("recall.title")}
      wide={mode === "local"}
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <strong>{target.title}</strong>
      {feedback ? (
        <>
          <details className="recall-submitted-page">
            <summary>{t("recall.viewSubmitted")}</summary>
            <img
              className="recall-page"
              src={`data:image/jpeg;base64,${feedback.image}`}
              alt={t("recall.submittedPage")}
            />
          </details>
          <RecallCorrection
            target={target}
            feedback={feedback.message}
            onSaved={onSaved}
            onClose={onClose}
          />
        </>
      ) : (
        <>
          <p>{t(mode === "camera" ? "recall.paperPrompt" : "recall.inkPrompt")}</p>
          {input.mode === "camera" ? <RecallVideo stream={input.stream} /> : null}
          {mode === "paired" && !ink && !error && pairUrl && qr ? (
            <div className="recall-pair">
              <img src={qr} width={210} height={210} alt={t("recall.qr")} />
              <p>{t("recall.scan")}</p>
              <a href={pairUrl} target="_blank" rel="noreferrer">
                {t("recall.openPad")}
              </a>
            </div>
          ) : null}
          {mode === "paired" && !pairUrl && !error ? (
            <p role="status">{t("recall.creating")}</p>
          ) : null}
          {ink ? (
            <img
              className="recall-page"
              src={`data:image/jpeg;base64,${ink}`}
              alt={t("recall.received")}
            />
          ) : null}
          {mode !== "paired" || ink ? <p>{t("recall.imagePrivacy")}</p> : null}
          {mode === "local" ? <HandwritingPad onSend={submit} sendLabel="recall.feedback" /> : null}
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}
          <div className="recall-actions">
            <button type="button" className="secondary-button" disabled={busy} onClick={onClose}>
              {t("recall.back")}
            </button>
            {mode !== "local" ? (
              <button
                type="button"
                className="primary-button"
                disabled={busy || (mode === "paired" && !ink)}
                onClick={() => void submit()}
              >
                {t(busy ? "recall.sending" : "recall.feedback")}
              </button>
            ) : null}
          </div>
        </>
      )}
    </Modal>
  );
}

function RecallVideo({ stream }: { stream: MediaProvider | null }) {
  const { t } = useI18n();
  const video = useRef<HTMLVideoElement>(null);
  useEffect(() => {
    const preview = video.current;
    if (!preview) return;
    preview.srcObject = stream;
    return () => {
      preview.srcObject = null;
    };
  }, [stream]);
  return (
    <video
      className="recall-page"
      ref={video}
      autoPlay
      muted
      playsInline
      aria-label={t("camera.preview")}
    />
  );
}

export function PairedInkDialog({
  lecture,
  code,
  onClose,
}: {
  lecture: InkLecture;
  code: string;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const [sent, setSent] = useState(false);
  return (
    <Modal title={t("recall.pad")} wide onClose={onClose}>
      {sent ? (
        <p role="status">{t("recall.sent")}</p>
      ) : (
        <>
          <p>{t("recall.inkPrompt")}</p>
          <HandwritingPad
            sendLabel="recall.sendDesktop"
            onSend={async (image) => {
              await inkPairRequest(lecture, "PUT", t("recall.pairFailed"), { code, image });
              setSent(true);
            }}
          />
        </>
      )}
      <button type="button" className="secondary-button" onClick={onClose}>
        {t("recall.back")}
      </button>
    </Modal>
  );
}
