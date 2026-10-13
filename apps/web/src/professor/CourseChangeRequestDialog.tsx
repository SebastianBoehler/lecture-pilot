import { useId } from "react";

import { useI18n } from "../i18n/i18n";
import { dismissDialogFromBackdrop } from "../shared/dialogBackdrop";
import type { LoginSession } from "../shared/types";
import { useModalDialog } from "../shared/useModalDialog";
import "./course-change-request.css";
import type { LectureState } from "./courseLectureStateTypes";
import { MAX_CHANGE_INSTRUCTION, useCanvasChangeRequest } from "./useCanvasChangeRequest";

/**
 * Describe a change to one lecture, optionally limited to some sections. The lecture then drafts
 * only those sections again; the professor reviews the draft before students see it.
 */
export function CourseChangeRequestDialog({
  courseId,
  lecture,
  session,
  onClose,
  onSubmitted,
}: {
  courseId: string;
  lecture: LectureState;
  session: LoginSession;
  onClose: () => void;
  onSubmitted: () => void;
}) {
  const { t } = useI18n();
  const dialogRef = useModalDialog();
  const titleId = useId();
  const instructionId = useId();
  const helpId = useId();
  const change = useCanvasChangeRequest({
    courseId,
    lectureId: lecture.lecture_id,
    session,
    onSubmitted,
  });
  const busy = change.submitting;
  const close = () => {
    if (!busy) onClose();
  };

  return (
    <dialog
      ref={dialogRef}
      className="course-update-dialog course-change-dialog"
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClick={(event) => dismissDialogFromBackdrop(event, close, busy)}
    >
      <header className="course-update-dialog-header">
        <h2 id={titleId}>{t("changeRequest.title")}</h2>
        <p>{t("changeRequest.lecture", { number: lecture.number, title: lecture.title })}</p>
      </header>
      <form
        id={`${titleId}-form`}
        className="course-update-dialog-body"
        onSubmit={(event) => {
          event.preventDefault();
          void change.submit();
        }}
      >
        <p className="lecture-panel-help" id={helpId}>
          {t("changeRequest.help")}
        </p>
        <div className="course-change-field">
          <label htmlFor={instructionId}>{t("changeRequest.instruction")}</label>
          <textarea
            id={instructionId}
            rows={5}
            maxLength={MAX_CHANGE_INSTRUCTION}
            required
            disabled={busy}
            aria-describedby={helpId}
            placeholder={t("changeRequest.placeholder")}
            value={change.instruction}
            onChange={(event) => change.setInstruction(event.target.value)}
          />
          <span className="course-change-count" aria-live="polite">
            {t("changeRequest.count", {
              count: change.instruction.length,
              max: MAX_CHANGE_INSTRUCTION,
            })}
          </span>
        </div>
        {change.options ? (
          <fieldset className="course-change-sections" disabled={busy}>
            <legend>{t("changeRequest.sections")}</legend>
            <p className="lecture-panel-help">{t("changeRequest.sectionsHelp")}</p>
            <ul>
              {change.options.sections.map((section) => (
                <li key={section.id}>
                  <label>
                    <input
                      type="checkbox"
                      checked={change.sectionIds.includes(section.id)}
                      onChange={() => change.toggleSection(section.id)}
                    />
                    <span>{section.title}</span>
                  </label>
                </li>
              ))}
            </ul>
          </fieldset>
        ) : !change.unavailable ? (
          <p role="status">{t("changeRequest.loading")}</p>
        ) : null}
        {change.options?.latest ? (
          <p className="course-change-latest">
            {t("changeRequest.latest", { instruction: change.options.latest.instruction })}
          </p>
        ) : null}
        {change.unavailable || change.error ? (
          <p className="form-error" role="alert">
            {change.unavailable ?? change.error}
          </p>
        ) : null}
      </form>
      <footer className="course-update-dialog-footer">
        <button className="course-row-button" type="button" disabled={busy} onClick={close}>
          {t("changeRequest.cancel")}
        </button>
        <button
          className="course-row-button"
          data-primary
          type="submit"
          form={`${titleId}-form`}
          disabled={!change.canSubmit}
          aria-busy={busy || undefined}
        >
          {busy ? t("changeRequest.submitting") : t("changeRequest.submit")}
        </button>
      </footer>
    </dialog>
  );
}
