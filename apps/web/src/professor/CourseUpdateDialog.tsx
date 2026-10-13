import { useId, useState } from "react";

import { useI18n } from "../i18n/i18n";
import { dismissDialogFromBackdrop } from "../shared/dialogBackdrop";
import type { LoginSession } from "../shared/types";
import { useModalDialog } from "../shared/useModalDialog";
import { useVersionUpdateActivity } from "../shell/VersionUpdateBoundary";
import { CourseUpdateReviewList } from "./CourseUpdateReviewList";
import { materialFilesFromDrop } from "./materialDrop";
import { materialSelectionSummary } from "./materialSelectionSummary";
import { useCourseUpdate } from "./useCourseUpdate";

/** Upload → compare → apply. Drafts are never started here; the course page takes over. */
export function CourseUpdateDialog({
  courseId,
  courseTitle,
  session,
  onApplied,
  onClose,
}: {
  courseId: string;
  courseTitle: string;
  session: LoginSession;
  onApplied: () => void;
  onClose: () => void;
}) {
  const { t } = useI18n();
  const dialogRef = useModalDialog();
  const titleId = useId();
  const fileInputId = useId();
  const folderInputId = useId();
  const [isDragOver, setIsDragOver] = useState(false);
  const update = useCourseUpdate(courseId, session, onApplied);
  const busy = Boolean(update.busy);
  useVersionUpdateActivity(busy || Boolean(update.analysis));
  const summary = materialSelectionSummary(update.files, {
    folderSummary: (folder, count) => t("builder.upload.folderSummary", { count, folder }),
    noFilesSelected: t("builder.upload.noFilesSelected"),
    selectedSummary: (count) => t("builder.upload.selectedSummary", { count }),
  });

  function close() {
    if (busy) return;
    void update.discard();
    onClose();
  }

  return (
    <dialog
      ref={dialogRef}
      className="course-update-dialog"
      aria-labelledby={titleId}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
      onClick={(event) => dismissDialogFromBackdrop(event, close, busy)}
    >
      <header className="course-update-dialog-header">
        <div>
          <h2 id={titleId}>{t("courseUpdate.dialogTitle")}</h2>
          <p>{courseTitle}</p>
        </div>
      </header>
      <div className="course-update-dialog-body">
        {!update.analysis ? (
          <>
            <p className="lecture-panel-help">{t("courseUpdate.dialogHelp")}</p>
            <div
              className={`material-drop-zone${isDragOver ? " is-drag-over" : ""}`}
              onDragOver={(event) => {
                event.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={(event) => {
                event.preventDefault();
                setIsDragOver(false);
                void materialFilesFromDrop(event.dataTransfer).then(update.chooseFiles);
              }}
            >
              <span className="material-drop-title">{t("courseUpdate.dropTitle")}</span>
              <div className="material-drop-actions">
                <label className="material-drop-button" htmlFor={fileInputId}>
                  {t("courseUpdate.chooseFiles")}
                </label>
                <label className="material-drop-button" htmlFor={folderInputId}>
                  {t("courseUpdate.chooseFolder")}
                </label>
              </div>
              <input
                id={fileInputId}
                className="material-drop-input"
                disabled={busy}
                multiple
                type="file"
                onChange={(event) => update.chooseFiles(Array.from(event.target.files ?? []))}
              />
              <input
                id={folderInputId}
                className="material-drop-input"
                disabled={busy}
                multiple
                type="file"
                onChange={(event) => update.chooseFiles(Array.from(event.target.files ?? []))}
                {...{ directory: "", webkitdirectory: "" }}
              />
            </div>
            <p className="material-selection-summary">{summary}</p>
          </>
        ) : (
          <>
            {update.ignored.length ? (
              <p className="lecture-panel-help">
                {t("courseUpdate.ignored", { count: update.ignored.length })}
              </p>
            ) : null}
            <CourseUpdateReviewList
              analysis={update.analysis}
              assignments={update.assignments}
              candidates={update.candidates}
              disabled={busy}
              manual={update.manual}
              selected={update.selected}
              onAssignment={update.setAssignment}
              onCandidateChange={update.updateCandidate}
              onManualChange={update.setManual}
              onToggle={update.toggleCandidate}
            />
            <p className="lecture-panel-help">
              {update.canApply ? t("courseUpdate.applyHelp") : t("courseUpdate.nothingSelected")}
            </p>
          </>
        )}
        {update.error ? (
          <p className="form-error" role="alert">
            {update.error}
          </p>
        ) : null}
      </div>
      <footer className="course-update-dialog-footer">
        <button className="course-row-button" type="button" disabled={busy} onClick={close}>
          {t("courseUpdate.cancel")}
        </button>
        {update.analysis ? (
          <>
            <button
              className="course-row-button"
              type="button"
              disabled={busy}
              onClick={() => update.chooseFiles([])}
            >
              {t("courseUpdate.changeFiles")}
            </button>
            <button
              className="course-row-button"
              data-primary
              type="button"
              disabled={busy || !update.canApply}
              onClick={() => void update.apply()}
            >
              {update.busy === "apply" ? t("courseUpdate.applying") : t("courseUpdate.apply")}
            </button>
          </>
        ) : (
          <button
            className="course-row-button"
            data-primary
            type="button"
            disabled={busy || !update.files.length}
            onClick={() => void update.compare()}
          >
            {update.busy === "upload"
              ? t("courseUpdate.uploading", update.uploadProgress)
              : update.busy === "analyze"
                ? t("courseUpdate.comparing")
                : t("courseUpdate.compare")}
          </button>
        )}
      </footer>
    </dialog>
  );
}
