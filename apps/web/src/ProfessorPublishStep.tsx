import { StepHeader } from "./ProfessorCourseBuilderParts";

export function ProfessorPublishStep({
  canPublish,
  onPublish,
  ready,
}: {
  canPublish: boolean;
  onPublish: () => void;
  ready: boolean;
}) {
  return (
    <section className="flow-card wide">
      <StepHeader number="05" title="Publish tutor workspace" done={ready} />
      <p className="drawer-note">Student dashboards show the AI tutor only after this course workspace is published.</p>
      <button disabled={!canPublish} type="button" onClick={onPublish}>
        Publish tutor workspace
      </button>
    </section>
  );
}
