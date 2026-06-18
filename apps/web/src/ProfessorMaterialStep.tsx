import { useId, useState } from "react";

import { fileRelativePath, materialFilesFromDrop } from "./materialDrop";
import { BundleSummary, PendingStatus, StepHeader } from "./ProfessorCourseBuilderParts";
import { ProfessorLectureSchedule } from "./ProfessorLectureSchedule";
import type { BuilderAction } from "./professorWorkflowRun";
import type { CourseSetup } from "./professorBuilderState";
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
  setup,
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
  setup: CourseSetup;
  uploadFiles: File[];
  uploadPath: string;
  workspaceReady: boolean;
}) {
  const inputId = useId();
  const [isDragOver, setIsDragOver] = useState(false);
  const isBusy = pendingAction !== null;
  const isUploading = pendingAction === "upload";
  const disabled = !courseReady || !workspaceReady || isBusy;
  const fileLabel = uploadFiles.length
    ? `${uploadFiles.length} selected`
    : "No files selected";
  return (
    <section className="flow-card">
      <StepHeader number="02" title="Upload materials" done={Boolean(bundle?.files.length)} />
      <label>
        Workspace folder
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
        <span className="material-drop-title">Drop course folder here</span>
        <span className="material-drop-copy">or choose a folder or files</span>
        <span className="material-drop-button">Choose materials</span>
        <input
          id={inputId}
          aria-label="Upload course material"
          className="material-drop-input"
          disabled={disabled}
          multiple
          onChange={(event) => onUploadFilesChange(Array.from(event.target.files ?? []))}
          type="file"
          {...{ directory: "", webkitdirectory: "" }}
        />
      </label>
      <p className="material-selection-summary">
        {fileLabel}
        {uploadFiles[0] ? <span>{fileRelativePath(uploadFiles[0])}</span> : null}
      </p>
      <div className="flow-actions">
        <button className="primary-action" disabled={disabled || !uploadFiles.length} type="button" onClick={onUpload}>
          {isUploading ? "Uploading materials..." : `Upload selected ${materialScope}`}
        </button>
        <button disabled={disabled} type="button" onClick={onScan}>
          {pendingAction === "scan" ? "Scanning uploaded bundle..." : "Scan uploaded bundle"}
        </button>
      </div>
      {pendingAction === "scan" ? <PendingStatus label="Refreshing uploaded source bundle..." /> : null}
      {isUploading ? <PendingStatus label="Uploading material and refreshing source bundle..." /> : null}
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
