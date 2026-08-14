import { useId, useMemo, useState } from "react";

import { useI18n } from "./i18n";
import { materialFilesFromDrop } from "./materialDrop";
import { materialSelectionSummary } from "./materialSelectionSummary";
import { preflightMaterialFiles } from "./professorUpload";
import { BundleSummary, PendingStatus, StepHeader } from "./ProfessorCourseBuilderParts";
import { ProfessorLectureSchedule } from "./ProfessorLectureSchedule";
import type { BuilderAction } from "./professorWorkflowRun";
import type { CourseMaterialUploadType, LectureScheduleItem, SourceBundleManifest } from "./types";

export function ProfessorMaterialStep({
  bundle,
  courseReady,
  lectureSchedule,
  onApplySchedule,
  onScheduleChange,
  onUpload,
  onUploadFilesChange,
  pendingAction,
  uploadFiles,
  supportedUploads,
  workspaceReady,
}: {
  bundle: SourceBundleManifest | null;
  courseReady: boolean;
  pendingAction: BuilderAction | null;
  lectureSchedule: LectureScheduleItem[];
  onApplySchedule: () => void;
  onScheduleChange: (schedule: LectureScheduleItem[]) => void;
  onUpload: () => void;
  onUploadFilesChange: (files: File[]) => void;
  uploadFiles: File[];
  supportedUploads: CourseMaterialUploadType[];
  workspaceReady: boolean;
}) {
  const { locale, t } = useI18n();
  const fileInputId = useId();
  const folderInputId = useId();
  const [isDragOver, setIsDragOver] = useState(false);
  const isBusy = pendingAction !== null;
  const isUploading = pendingAction === "upload";
  const disabled = !courseReady || !workspaceReady || isBusy;
  const preflight = useMemo(
    () => preflightMaterialFiles(uploadFiles, supportedUploads),
    [supportedUploads, uploadFiles],
  );
  const fileLabel = materialSelectionSummary(uploadFiles, {
    folderSummary: (folder, count) => t("builder.upload.folderSummary", { count, folder }),
    noFilesSelected: t("builder.upload.noFilesSelected"),
    selectedSummary: (count) => t("builder.upload.selectedSummary", { count }),
  });
  return (
    <section className="flow-card">
      <StepHeader
        number="02"
        title={t("builder.upload.title")}
        done={Boolean(bundle?.files.length)}
      />
      <div
        className={`material-drop-zone${isDragOver ? " is-drag-over" : ""}${disabled ? " is-disabled" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(event) => {
          event.preventDefault();
          setIsDragOver(false);
          if (!disabled) void materialFilesFromDrop(event.dataTransfer).then(onUploadFilesChange);
        }}
      >
        <span className="material-drop-title">{t("courseUpdate.dropTitle")}</span>
        <span className="material-drop-copy">{t("builder.upload.dropCopy")}</span>
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
          disabled={disabled}
          multiple
          onChange={(event) => onUploadFilesChange(Array.from(event.target.files ?? []))}
          type="file"
        />
        <input
          id={folderInputId}
          className="material-drop-input"
          disabled={disabled}
          multiple
          onChange={(event) => onUploadFilesChange(Array.from(event.target.files ?? []))}
          type="file"
          {...{ directory: "", webkitdirectory: "" }}
        />
      </div>
      <p className="material-format-note">{t("builder.upload.formats")}</p>
      <p className="material-selection-summary">{fileLabel}</p>
      {uploadFiles.length && supportedUploads.length ? (
        <>
          <p className="material-preflight-summary">
            {locale === "de"
              ? `${preflight.accepted.length} zum Hochladen · ${preflight.excluded.length} vor dem Transfer abgelehnt`
              : `${preflight.accepted.length} ready to upload · ${preflight.excluded.length} rejected before transfer`}
          </p>
          {preflight.excluded.length ? (
            <ul aria-label={t("builder.upload.rejectedFiles")} className="material-rejection-list">
              {preflight.excluded.slice(0, 5).map((item) => (
                <li key={`${item.path}:${item.reason}`}>
                  {item.path} · {t("builder.upload.rejected")} ·{" "}
                  {t(`builder.upload.rejection.${item.reason}`)}
                </li>
              ))}
            </ul>
          ) : null}
        </>
      ) : null}
      <div className="flow-actions">
        <button
          className="primary-action"
          disabled={disabled || !preflight.accepted.length}
          type="button"
          onClick={onUpload}
        >
          {isUploading ? t("builder.upload.uploading") : t("builder.upload.uploadSelected")}
        </button>
      </div>
      {isUploading ? <PendingStatus label={t("builder.upload.uploadingStatus")} /> : null}
      {bundle ? <BundleSummary bundle={bundle} /> : null}
      <ProfessorLectureSchedule
        disabled={!lectureSchedule.length || isBusy}
        isApplying={pendingAction === "apply-schedule"}
        schedule={lectureSchedule}
        onChange={onScheduleChange}
        onApply={onApplySchedule}
      />
    </section>
  );
}
