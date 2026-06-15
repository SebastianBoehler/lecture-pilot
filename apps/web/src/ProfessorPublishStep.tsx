import { PendingStatus, StepHeader } from "./ProfessorCourseBuilderParts";

export function ProfessorPublishStep({
  canPublish,
  isPublishing,
  onPublish,
  ready,
}: {
  canPublish: boolean;
  isPublishing: boolean;
  onPublish: () => void;
  ready: boolean;
}) {
  return (
    <section className="flow-card wide">
      <StepHeader number="05" title="Publish tutor workspace" done={ready} />
      <p className="drawer-note">Student dashboards show the AI tutor only after this course workspace is published.</p>
      <button disabled={!canPublish || isPublishing} type="button" onClick={onPublish}>
        {isPublishing ? "Publishing workspace..." : "Publish tutor workspace"}
      </button>
      {isPublishing ? <PendingStatus label="Publishing tutor workspace for students..." /> : null}
    </section>
  );
}
