import { useId, useState } from "react";

import { useI18n } from "./i18n";
import { materialFilesFromDrop } from "./materialDrop";
import { materialSelectionSummary } from "./materialSelectionSummary";
import { BundleSummary, PendingStatus, StepHeader } from "./ProfessorCourseBuilderParts";
import { ProfessorLectureSchedule } from "./ProfessorLectureSchedule";
import type { BuilderAction } from "./professorWorkflowRun";
import type { LectureScheduleItem, SourceBundleManifest } from "./types";

export function ProfessorMaterialStep({
  bundle,
  courseReady,
  lectureSchedule,
  materialScope,
  onApplySchedule,
  onScheduleChange,
  onScan,
  onUpload,
  onUploadFilesChange,
  pendingAction,
  setUploadPath,
  uploadFiles,
  uploadPath,
  workspaceReady,
}: {
  bundle: SourceBundleManifest | null;
  courseReady: boolean;
  pendingAction: BuilderAction | null;
  lectureSchedule: LectureScheduleItem[];
  materialScope: string;
  onApplySchedule: () => void;
  onScan: () => void;
  onScheduleChange: (schedule: LectureScheduleItem[]) => void;
  onUpload: () => void;
  onUploadFilesChange: (files: File[]) => void;
  setUploadPath: (path: string) => void;
  uploadFiles: File[];
  uploadPath: string;
  workspaceReady: boolean;
}) {
  const { t } = useI18n();
  const inputId = useId();
  const [isDragOver, setIsDragOver] = useState(false);
  const isBusy = pendingAction !== null;
  const isUploading = pendingAction === "upload";
  const disabled = !courseReady || !workspaceReady || isBusy;
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
      <label>
        {t("builder.upload.folder")}
        <input value={uploadPath} onChange={(event) => setUploadPath(event.target.value)} />
      </label>
      <label
        className={`material-drop-zone${isDragOver ? " is-drag-over" : ""}${disabled ? " is-disabled" : ""}`}
        htmlFor={inputId}
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
        <span className="material-drop-title">{t("builder.upload.dropTitle")}</span>
        <span className="material-drop-copy">{t("builder.upload.dropCopy")}</span>
        <span className="material-drop-button">{t("builder.upload.choose")}</span>
        <input
          id={inputId}
          aria-label={t("builder.upload.aria")}
          className="material-drop-input"
          disabled={disabled}
          multiple
          onChange={(event) => onUploadFilesChange(Array.from(event.target.files ?? []))}
          type="file"
          {...{ directory: "", webkitdirectory: "" }}
        />
      </label>
      <p className="material-selection-summary">{fileLabel}</p>
      <div className="flow-actions">
        <button
          className="primary-action"
          disabled={disabled || !uploadFiles.length}
          type="button"
          onClick={onUpload}
        >
          {isUploading
            ? t("builder.upload.uploading")
            : t("builder.upload.uploadSelected", { scope: materialScope })}
        </button>
        <button disabled={disabled} type="button" onClick={onScan}>
          {pendingAction === "scan" ? t("builder.upload.scanning") : t("builder.upload.scan")}
        </button>
      </div>
      {pendingAction === "scan" ? <PendingStatus label={t("builder.upload.refreshing")} /> : null}
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
