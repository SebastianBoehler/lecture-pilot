import { BundleSummary, StepHeader } from "./ProfessorCourseBuilderParts";
import { ProfessorLectureSchedule } from "./ProfessorLectureSchedule";
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
  setUploadPath,
  setup,
  uploadFiles,
  uploadPath,
  workspaceReady,
}: {
  bundle: SourceBundleManifest | null;
  courseReady: boolean;
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
        disabled={!courseReady || !workspaceReady}
        multiple
        onChange={(event) => onUploadFilesChange(Array.from(event.target.files ?? []))}
        type="file"
        {...{ directory: "", webkitdirectory: "" }}
      />
      <div className="flow-actions">
        <button disabled={!courseReady || !workspaceReady || !uploadFiles.length} type="button" onClick={onUpload}>
          Upload material
        </button>
        <button disabled={!courseReady || !workspaceReady} type="button" onClick={onScan}>
          Scan source bundle
        </button>
      </div>
      {bundle ? <BundleSummary bundle={bundle} /> : null}
      <ProfessorLectureSchedule
        disabled={!lectureSchedule.length}
        schedule={lectureSchedule}
        onChange={onScheduleChange}
        onApply={onApplySchedule}
      />
    </section>
  );
}
