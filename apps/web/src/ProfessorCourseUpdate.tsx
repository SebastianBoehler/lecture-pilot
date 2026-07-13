import { useId, useState } from "react";

import { CourseUpdateReview } from "./CourseUpdateReview";
import { useI18n } from "./i18n";
import { materialFilesFromDrop } from "./materialDrop";
import { materialSelectionSummary } from "./materialSelectionSummary";
import type { CourseWorkspaceResult, LoginSession } from "./types";
import { useCourseUpdate } from "./useCourseUpdate";

export function ProfessorCourseUpdate({
  onBack,
  onWorkspaceUpdated,
  session,
  workspace,
}: {
  onBack: () => void;
  onWorkspaceUpdated: (workspace: CourseWorkspaceResult) => void;
  session: LoginSession;
  workspace: CourseWorkspaceResult;
}) {
  const { t } = useI18n();
  const fileInputId = useId();
  const folderInputId = useId();
  const [isDragOver, setIsDragOver] = useState(false);
  const update = useCourseUpdate(workspace, session, onWorkspaceUpdated);
  const summary = materialSelectionSummary(update.files, {
    folderSummary: (folder, count) => t("builder.upload.folderSummary", { count, folder }),
    noFilesSelected: t("builder.upload.noFilesSelected"),
    selectedSummary: (count) => t("builder.upload.selectedSummary", { count }),
  });
  const readyCount = Object.values(update.statuses).filter((status) => status === "ready").length;
  const failedCount = Object.values(update.statuses).filter((status) => status === "failed").length;
  const publishedCount = Object.values(update.statuses).filter(
    (status) => status === "published",
  ).length;

  return (
    <main className="professor-screen course-update-page">
      <header className="professor-page-header">
        <div>
          <button
            className="refresh-button course-update-back"
            disabled={Boolean(update.busy)}
            type="button"
            onClick={handleBack}
          >
            {t("courseUpdate.back")}
          </button>
          <h1>{t("courseUpdate.pageTitle", { course: workspace.course.title })}</h1>
          <p>{t("courseUpdate.pageHelp")}</p>
        </div>
      </header>

      {!update.analysis && !update.result ? (
        <section className="course-update-upload" aria-labelledby="course-update-upload-title">
          <div>
            <h2 id="course-update-upload-title">{t("courseUpdate.uploadTitle")}</h2>
            <p>{t("courseUpdate.uploadHelp")}</p>
          </div>
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
              void materialFilesFromDrop(event.dataTransfer).then(update.setFiles);
            }}
          >
            <strong>{t("courseUpdate.dropTitle")}</strong>
            <span>{t("courseUpdate.dropHelp")}</span>
            <div className="course-update-file-actions">
              <label className="refresh-button" htmlFor={fileInputId}>
                {t("courseUpdate.chooseFiles")}
              </label>
              <label className="refresh-button" htmlFor={folderInputId}>
                {t("courseUpdate.chooseFolder")}
              </label>
            </div>
            <input
              id={fileInputId}
              className="material-drop-input"
              multiple
              type="file"
              onChange={(event) => update.setFiles(Array.from(event.target.files ?? []))}
            />
            <input
              id={folderInputId}
              className="material-drop-input"
              multiple
              type="file"
              onChange={(event) => update.setFiles(Array.from(event.target.files ?? []))}
              {...{ directory: "", webkitdirectory: "" }}
            />
          </div>
          <p className="material-format-note">{t("builder.upload.formats")}</p>
          <p className="material-selection-summary">{summary}</p>
          <button
            className="primary-action"
            disabled={!update.files.length || Boolean(update.busy)}
            type="button"
            onClick={() => void update.compare()}
          >
            {update.busy === "upload"
              ? t("courseUpdate.uploading", update.uploadProgress)
              : update.busy === "analyze"
                ? t("courseUpdate.comparing")
                : t("courseUpdate.compare")}
          </button>
        </section>
      ) : null}

      {update.analysis && !update.result ? (
        <>
          <section
            className="course-update-source-summary"
            aria-label={t("courseUpdate.sourceSummary")}
          >
            <div>
              <strong>
                {t(
                  update.files.length === 1
                    ? "courseUpdate.selectionSummaryOne"
                    : "courseUpdate.selectionSummary",
                  { count: update.files.length },
                )}
              </strong>
              <span>{changeSummary(update.analysis, t)}</span>
            </div>
            <button
              className="refresh-button"
              disabled={Boolean(update.busy)}
              type="button"
              onClick={() => update.setFiles([])}
            >
              {t("courseUpdate.changeSelection")}
            </button>
          </section>
          {update.ignored.length ? (
            <p className="course-update-notice">
              {t("courseUpdate.ignored", { count: update.ignored.length })}
            </p>
          ) : null}
          <CourseUpdateReview
            analysis={update.analysis}
            assignments={update.assignments}
            candidates={update.candidates}
            disabled={Boolean(update.busy)}
            manual={update.manual}
            selected={update.selected}
            onAssignment={update.setAssignment}
            onCandidateChange={update.updateCandidate}
            onManualChange={update.setManual}
            onToggle={update.toggleCandidate}
          />
          {update.analysis.candidates.length || update.analysis.unassigned_files.length ? (
            <div className="course-update-submit">
              <p>{t("courseUpdate.publishGuard")}</p>
              <button
                className="primary-action"
                disabled={!update.hasSelection || Boolean(update.busy)}
                type="button"
                onClick={() => void update.apply()}
              >
                {update.busy ? t("courseUpdate.preparing") : t("courseUpdate.prepareDrafts")}
              </button>
            </div>
          ) : null}
        </>
      ) : null}

      {update.result ? (
        <section className="course-update-result" aria-labelledby="course-update-result-title">
          <h2 id="course-update-result-title">{t("courseUpdate.draftsTitle")}</h2>
          <p>{t("courseUpdate.draftsHelp")}</p>
          <ul>
            {update.result.affected_lecture_ids.map((lectureId) => (
              <li key={lectureId}>
                <span>{lectureTitle(update.result?.workspace, lectureId)}</span>
                <strong>{statusLabel(update.statuses[lectureId], t)}</strong>
              </li>
            ))}
          </ul>
          <div className="flow-actions">
            {failedCount ? (
              <button
                disabled={Boolean(update.busy)}
                type="button"
                onClick={() => void update.retryDrafts()}
              >
                {t("courseUpdate.retryDrafts")}
              </button>
            ) : null}
            {readyCount ? (
              <button
                className="primary-action"
                disabled={Boolean(update.busy)}
                type="button"
                onClick={() => void update.publish()}
              >
                {update.busy === "publish"
                  ? t("courseUpdate.publishing")
                  : t("courseUpdate.publishDrafts", { count: readyCount })}
              </button>
            ) : null}
            {publishedCount === update.result.affected_lecture_ids.length ? (
              <button className="primary-action" type="button" onClick={onBack}>
                {t("courseUpdate.done")}
              </button>
            ) : null}
          </div>
        </section>
      ) : null}
      {update.error ? <p className="form-error">{update.error}</p> : null}
    </main>
  );

  function handleBack() {
    void update.cancel().finally(onBack);
  }
}

function lectureTitle(workspace: CourseWorkspaceResult | undefined, lectureId: string) {
  return workspace?.lectures.find((lecture) => lecture.id === lectureId)?.title ?? lectureId;
}

function statusLabel(status: string | undefined, t: ReturnType<typeof useI18n>["t"]) {
  return t(`courseUpdate.status.${status ?? "waiting"}` as Parameters<typeof t>[0]);
}

function changeSummary(
  analysis: NonNullable<ReturnType<typeof useCourseUpdate>["analysis"]>,
  t: ReturnType<typeof useI18n>["t"],
) {
  const count =
    analysis.candidates.reduce((total, candidate) => total + candidate.file_paths.length, 0) +
    analysis.unassigned_files.length;
  return t(count === 1 ? "courseUpdate.changeSummaryOne" : "courseUpdate.changeSummary", {
    count,
  });
}
