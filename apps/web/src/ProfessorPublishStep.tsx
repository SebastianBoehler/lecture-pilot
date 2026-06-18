import { PendingStatus, StepHeader } from "./ProfessorCourseBuilderParts";

export function ProfessorPublishStep({
  canPublish,
  isFullCourse,
  isPublishing,
  lectures,
  onPublish,
  publishedCount,
  ready,
  totalCount,
}: {
  canPublish: boolean;
  isFullCourse: boolean;
  isPublishing: boolean;
  lectures: {
    id: string;
    label: string;
    previewHref: string;
    published: boolean;
  }[];
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
      {ready ? (
        <p className="drawer-note">Published workspaces are available from student dashboards.</p>
      ) : (
        <p className="drawer-note">Student dashboards show the AI tutor only after this course workspace is published.</p>
      )}
      {isFullCourse ? <p>{publishedCount} of {totalCount} lecture workspaces published.</p> : null}
      {!ready ? (
        <button className="primary-action" disabled={!canPublish || isPublishing} type="button" onClick={onPublish}>
          {isPublishing ? busyLabel : actionLabel}
        </button>
      ) : null}
      {isPublishing ? <PendingStatus label={statusLabel} /> : null}
      {ready ? <PublishedLectureList lectures={lectures} /> : null}
    </section>
  );
}

function PublishedLectureList({
  lectures,
}: {
  lectures: {
    id: string;
    label: string;
    previewHref: string;
    published: boolean;
  }[];
}) {
  if (!lectures.length) return null;
  return (
    <div className="published-lecture-list" aria-label="Published lecture workspaces">
      <header>
        <strong>Published lecture workspaces</strong>
        <span>Review each lecture before sending students into the course.</span>
      </header>
      {lectures.map((lecture) => (
        <div className="published-lecture-row" key={lecture.id}>
          <span>{lecture.label}</span>
          <strong>{lecture.published ? "Published" : "Pending"}</strong>
          <a className="button-link" href={lecture.previewHref} rel="noreferrer" target="_blank">
            Preview
          </a>
        </div>
      ))}
    </div>
  );
}
