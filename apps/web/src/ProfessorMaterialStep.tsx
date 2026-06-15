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
  onScheduleChange: (schedule: LectureScheduleItem[]) => void;
  onScan: () => void;
  onUpload: () => void;
  onUploadFilesChange: (files: File[]) => void;
  setUploadPath: (path: string) => void;
  setup: CourseSetup;
  uploadFiles: File[];
  uploadPath: string;
  workspaceReady: boolean;
}) {
  const isBusy = pendingAction !== null;
  const isUploading = pendingAction === "upload";
  const isScanning = pendingAction === "scan";
  return (
    <section className="flow-card">
      <StepHeader number="02" title="Upload and scan materials" done={Boolean(bundle)} />
      <p className="drawer-note">Upload {materialScope} for {setup.courseTitle}.</p>
      <label>
        Store uploaded files under
        <input value={uploadPath} onChange={(event) => setUploadPath(event.target.value)} />
      </label>
      <input
        aria-label="Upload course material"
        disabled={!courseReady || !workspaceReady || isBusy}
        multiple
        onChange={(event) => onUploadFilesChange(Array.from(event.target.files ?? []))}
        type="file"
        {...{ directory: "", webkitdirectory: "" }}
      />
      <div className="flow-actions">
        <button disabled={!courseReady || !workspaceReady || !uploadFiles.length || isBusy} type="button" onClick={onUpload}>
          {isUploading ? "Uploading material..." : "Upload material"}
        </button>
        <button disabled={!courseReady || !workspaceReady || isBusy} type="button" onClick={onScan}>
          {isScanning ? "Scanning source bundle..." : "Scan source bundle"}
        </button>
      </div>
      {isUploading ? <PendingStatus label="Uploading material and refreshing source bundle..." /> : null}
      {isScanning ? <PendingStatus label="Scanning source bundle and checking lecture schedule..." /> : null}
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
