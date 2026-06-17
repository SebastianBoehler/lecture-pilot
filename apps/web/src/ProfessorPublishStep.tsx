import { PendingStatus, StepHeader } from "./ProfessorCourseBuilderParts";

export function ProfessorPublishStep({
  canPublish,
  isFullCourse,
  isPublishing,
  onPublish,
  publishedCount,
  ready,
  totalCount,
}: {
  canPublish: boolean;
  isFullCourse: boolean;
  isPublishing: boolean;
  onPublish: () => void;
  publishedCount: number;
  ready: boolean;
  totalCount: number;
}) {
  const actionLabel = isFullCourse ? "Publish all tutor workspaces" : "Publish tutor workspace";
  const busyLabel = isFullCourse ? "Publishing tutor workspaces..." : "Publishing workspace...";
  const statusLabel = isFullCourse
    ? `Publishing ${totalCount} tutor workspaces for students...`
    : "Publishing tutor workspace for students...";
  return (
    <section className="flow-card wide">
      <StepHeader number="05" title="Publish tutor workspace" done={ready} />
      <p className="drawer-note">Student dashboards show the AI tutor only after this course workspace is published.</p>
      {isFullCourse ? <p>{publishedCount} of {totalCount} lecture workspaces published.</p> : null}
      <button disabled={!canPublish || isPublishing} type="button" onClick={onPublish}>
        {isPublishing ? busyLabel : actionLabel}
      </button>
      {isPublishing ? <PendingStatus label={statusLabel} /> : null}
    </section>
  );
}
