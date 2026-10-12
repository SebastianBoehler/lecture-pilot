import { ExternalLink, X } from "lucide-react";
import { useState } from "react";

import { buildFeedbackMailto, type FeedbackCategory } from "./feedbackMailto";
import { dismissDialogFromBackdrop } from "./dialogBackdrop";
import { useI18n } from "./i18n";
import type { FeedbackPromptSource } from "./useFeedbackPrompt";
import { useModalDialog } from "./useModalDialog";

export type FeedbackContext = {
  courseTitle?: string;
  lectureTitle?: string;
};

/** Rendered only while open; remount it (e.g. keyed by source) to start a fresh draft. */
export function FeedbackDialog({
  accountType,
  context,
  source,
  onClose,
}: {
  accountType: "student" | "professor";
  context: FeedbackContext;
  source: FeedbackPromptSource;
  onClose: () => void;
}) {
  const { locale, t } = useI18n();
  const dialogRef = useModalDialog();
  const [category, setCategory] = useState<FeedbackCategory>("feedback");
  const [message, setMessage] = useState("");

  const href = buildFeedbackMailto({
    accountType,
    appVersion: __LECTUREPILOT_APP_VERSION__,
    browser: window.navigator.userAgent,
    buildId: __LECTUREPILOT_BUILD_ID__,
    category,
    courseTitle: context.courseTitle,
    lectureTitle: context.lectureTitle,
    locale,
    message,
    pageUrl: window.location.href,
  });
  const title = source === "threshold" ? t("feedback.promptTitle") : t("feedback.title");

  return (
    <dialog
      aria-labelledby="feedback-dialog-title"
      aria-modal="true"
      className="feedback-dialog"
      onClick={(event) => dismissDialogFromBackdrop(event, onClose)}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      ref={dialogRef}
    >
      <header className="feedback-dialog-header">
        <h2 id="feedback-dialog-title">{title}</h2>
        <button aria-label={t("feedback.close")} type="button" onClick={onClose}>
          <X size={17} />
        </button>
      </header>
      <div className="feedback-dialog-body">
        <p>
          {source === "threshold" ? t("feedback.promptDescription") : t("feedback.description")}
        </p>
        <label>
          <span>{t("feedback.category")}</span>
          <select
            aria-label={t("feedback.category")}
            value={category}
            onChange={(event) => setCategory(event.target.value as FeedbackCategory)}
          >
            <option value="feedback">{t("feedback.category.feedback")}</option>
            <option value="feature">{t("feedback.category.feature")}</option>
            <option value="bug">{t("feedback.category.bug")}</option>
          </select>
        </label>
        <label>
          <span>{t("feedback.message")}</span>
          <textarea
            aria-label={t("feedback.message")}
            onChange={(event) => setMessage(event.target.value)}
            placeholder={t("feedback.messagePlaceholder")}
            rows={6}
            value={message}
          />
        </label>
        <p className="feedback-diagnostics">{t("feedback.diagnostics")}</p>
      </div>
      <footer className="feedback-dialog-footer">
        <button type="button" onClick={onClose}>
          {t("feedback.cancel")}
        </button>
        <a className="feedback-email-link" href={href}>
          {t("feedback.openEmail")}
          <ExternalLink size={15} />
        </a>
      </footer>
    </dialog>
  );
}
