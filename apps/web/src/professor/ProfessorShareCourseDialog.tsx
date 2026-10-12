import QRCode from "qrcode";
import { useEffect, useId, useState } from "react";

import {
  courseUrl,
  disableCourseInvite,
  getCourseInvite,
  inviteUrl,
  rotateCourseInvite,
  type CourseInvite,
} from "./courseInviteApi";
import { dismissDialogFromBackdrop } from "../shared/dialogBackdrop";
import "./share-course.css";
import { translate, useI18n } from "../i18n/i18n";
import { useModalDialog } from "../shared/useModalDialog";
import type { LoginSession, ManagedCourseWorkspaceResult } from "../shared/types";
import { renderShareSlide } from "./shareSlide";

export function ProfessorShareCourseDialog({
  session,
  workspace,
  onClose,
}: {
  session: LoginSession;
  workspace: ManagedCourseWorkspaceResult;
  onClose: () => void;
}) {
  const { locale, t } = useI18n();
  const dialogRef = useModalDialog();
  const titleId = useId();
  // null: only enrolled students (Alma/ILIAS) can open the course; an invite also lets others join.
  const [invite, setInvite] = useState<CourseInvite | null | undefined>(undefined);
  const [qr, setQr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const courseId = workspace.course.id;
  const instructorsOnly = workspace.accessSummary.default_rule.audience === "instructors_only";
  const url = invite ? inviteUrl(invite) : courseUrl(courseId);

  useEffect(() => {
    let cancelled = false;
    getCourseInvite(courseId, session)
      .then((current) => !cancelled && setInvite(current))
      .catch((loadError: unknown) => {
        if (!cancelled)
          setError(loadError instanceof Error ? loadError.message : String(loadError));
      });
    return () => {
      cancelled = true;
    };
  }, [courseId, session]);

  useEffect(() => {
    let cancelled = false;
    void QRCode.toString(url, { type: "svg", margin: 1, errorCorrectionLevel: "M" }).then(
      (svg) => !cancelled && setQr(svg),
    );
    setCopied(false);
    return () => {
      cancelled = true;
    };
  }, [url]);

  async function update(action: () => Promise<CourseInvite | null>) {
    setBusy(true);
    setError(null);
    try {
      setInvite(await action());
    } catch (updateError) {
      setError(updateError instanceof Error ? updateError.message : String(updateError));
    } finally {
      setBusy(false);
    }
  }

  async function downloadSlide() {
    // Students read the slide in the lecture, so it follows the course's teaching language.
    const slideT = translate(workspace.course.canvas_language ?? locale);
    const { title, term, professor } = workspace.course;
    const link = document.createElement("a");
    link.href = await renderShareSlide({
      url,
      title,
      meta: [term, professor].filter(Boolean).join(" · "),
      texts: {
        eyebrow: slideT("share.slideEyebrow"),
        steps: [
          slideT("share.slideStep1"),
          slideT(invite ? "share.slideStep2Join" : "share.slideStep2"),
          slideT("share.slideStep3"),
        ],
        scan: slideT("share.slideScan"),
      },
    });
    link.download = `${workspace.course.title.replace(/[^\w-]+/g, "-")}-lecturepilot.png`;
    link.click();
  }

  return (
    <dialog
      aria-labelledby={titleId}
      aria-modal="true"
      className="course-access-dialog share-course-dialog"
      ref={dialogRef}
      onClick={(event) => dismissDialogFromBackdrop(event, onClose, busy)}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
    >
      <header className="course-access-dialog-header">
        <div>
          <h2 id={titleId}>{t("share.title", { course: workspace.course.title })}</h2>
          <p>{t(invite ? "share.helpJoin" : "share.helpEnrolled")}</p>
        </div>
      </header>
      <div className="course-access-dialog-body">
        {qr ? (
          <div
            aria-label={t("share.qrLabel")}
            className="share-qr"
            role="img"
            dangerouslySetInnerHTML={{ __html: qr }}
          />
        ) : null}
        <label className="share-link">
          {t("share.link")}
          <input readOnly value={url} onFocus={(event) => event.target.select()} />
        </label>
        <div className="share-actions">
          <button
            className="primary-action"
            type="button"
            onClick={() => void navigator.clipboard?.writeText(url).then(() => setCopied(true))}
          >
            {copied ? t("share.copied") : t("share.copy")}
          </button>
          <button type="button" onClick={() => void downloadSlide()}>
            {t("share.slide")}
          </button>
        </div>
        <label className="share-join-toggle">
          <input
            type="checkbox"
            checked={Boolean(invite)}
            disabled={busy || invite === undefined || instructorsOnly}
            onChange={(event) =>
              void update(async () => {
                if (event.target.checked) return rotateCourseInvite(courseId, session);
                await disableCourseInvite(courseId, session);
                return null;
              })
            }
          />
          <span>
            <strong>{t("share.allowJoin")}</strong>
            {t(instructorsOnly ? "share.instructorsOnly" : "share.allowJoinHelp")}
          </span>
        </label>
        {invite ? (
          <button
            type="button"
            disabled={busy}
            onClick={() => void update(() => rotateCourseInvite(courseId, session))}
          >
            {t("share.rotate")}
          </button>
        ) : null}
        {error ? <p className="form-error">{error}</p> : null}
      </div>
      <footer className="course-access-dialog-footer">
        <button type="button" disabled={busy} onClick={onClose}>
          {t("share.close")}
        </button>
      </footer>
    </dialog>
  );
}
