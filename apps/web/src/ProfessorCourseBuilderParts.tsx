import type { CanvasDocument, SourceBundleManifest, YoutubeVideoCandidate } from "./types";
import type { CourseSetup } from "./professorBuilderState";
import type { YoutubeCandidateGroup } from "./professorYoutubeSuggestions";

export function StepHeader({ number, title, done }: { number: string; title: string; done: boolean }) {
  return <header className="step-header"><span>{number}</span><h2>{title}</h2><strong>{done ? "Ready" : "Pending"}</strong></header>;
}

export function PendingStatus({ label }: { label: string }) {
  return (
    <p className="flow-status" role="status">
      <span aria-hidden="true" />
      {label}
    </p>
  );
}

export function CourseSetupStep({
  courseReady,
  isCreating,
  isReady,
  onCreate,
  onSetupChange,
  setup,
}: {
  courseReady: boolean;
  isCreating: boolean;
  isReady: boolean;
  onCreate: () => void;
  onSetupChange: (setup: CourseSetup) => void;
  setup: CourseSetup;
}) {
  return (
    <section className="flow-card wide">
      <StepHeader number="01" title="Define course and lecture scope" done={courseReady} />
      <label>
        Course name
        <input value={setup.courseTitle} onChange={(event) => onSetupChange({ ...setup, courseTitle: event.target.value })} />
      </label>
      <label>
        Course visibility
        <select
          value={setup.accessPolicy}
          onChange={(event) => onSetupChange({ ...setup, accessPolicy: event.target.value as CourseSetup["accessPolicy"] })}
        >
          <option value="tuebingen_enrolled">Course students only</option>
          <option value="platform_authenticated">University-wide login</option>
          <option value="public">Public on the platform</option>
        </select>
      </label>
      <div className="scope-toggle" role="group" aria-label="Canvas generation scope">
        <button className={setup.target === "single-lecture" ? "is-active" : ""} type="button" onClick={() => onSetupChange({ ...setup, target: "single-lecture" })}>
          Specific lecture
        </button>
        <button className={setup.target === "full-course" ? "is-active" : ""} type="button" onClick={() => onSetupChange({ ...setup, target: "full-course", lectureCount: "" })}>
          Full course
        </button>
      </div>
      {setup.target === "single-lecture" ? (
        <div className="flow-grid">
          <label>
            Lecture number
            <input value={setup.lectureNumber} onChange={(event) => onSetupChange({ ...setup, lectureNumber: event.target.value })} />
          </label>
          <label>
            Lecture title
            <input value={setup.lectureTitle} onChange={(event) => onSetupChange({ ...setup, lectureTitle: event.target.value })} />
          </label>
        </div>
      ) : (
        <div className="flow-grid course-scope-grid">
          <label>
            Expected lectures (optional)
            <input
              min="1"
              placeholder="Infer from materials"
              type="number"
              value={setup.lectureCount}
              onChange={(event) => onSetupChange({ ...setup, lectureCount: event.target.value })}
            />
          </label>
          <label>
            First lecture date
            <input
              placeholder="YYYY-MM-DD"
              value={setup.firstLectureDate}
              onChange={(event) => onSetupChange({ ...setup, firstLectureDate: event.target.value })}
            />
          </label>
        </div>
      )}
      <button className="primary-action" disabled={!isReady || isCreating} type="button" onClick={onCreate}>
        {isCreating ? "Creating workspace..." : "Create course workspace"}
      </button>
      {isCreating ? <PendingStatus label="Creating course workspace..." /> : null}
    </section>
  );
}

export function BundleSummary({ bundle }: { bundle: SourceBundleManifest }) {
  if (!bundle.files.length) return <p>No materials indexed yet.</p>;
  return <p>{bundle.files.length} files indexed · {Object.entries(bundle.counts_by_kind).map(([kind, count]) => `${count} ${kind}`).join(", ")}</p>;
}

export function VideoCandidateGroups({
  groups,
  onToggle,
  selectedVideos,
}: {
  groups: YoutubeCandidateGroup[];
  onToggle: (videoId: string) => void;
  selectedVideos: Set<string>;
}) {
  if (!groups.length) return null;
  return (
    <div className="video-candidate-groups">
      {groups.map((group) => (
        <section className="video-candidate-group" key={group.query}>
          <h3>{group.query}</h3>
          <VideoCandidates
            emptyLabel="No strong candidates for this query."
            videos={group.videos}
            selectedVideos={selectedVideos}
            onToggle={onToggle}
          />
        </section>
      ))}
    </div>
  );
}

export function VideoCandidates({ emptyLabel = "No candidates searched yet.", videos, selectedVideos, onToggle }: {
  emptyLabel?: string;
  videos: YoutubeVideoCandidate[];
  selectedVideos: Set<string>;
  onToggle: (videoId: string) => void;
}) {
  if (!videos.length) return <p className="drawer-note">{emptyLabel}</p>;
  return (
    <div className="video-candidate-list">
      {videos.map((video) => (
        <div className="video-candidate" key={video.video_id}>
          <label className="video-candidate-choice">
            <input
              checked={selectedVideos.has(video.video_id)}
              onChange={() => onToggle(video.video_id)}
              type="checkbox"
            />
            <span><strong>{video.title}</strong>{video.channel_title} · {video.duration.display ?? "duration unknown"}</span>
          </label>
          <a className="video-preview-link" href={video.url} rel="noreferrer" target="_blank">
            Open
          </a>
        </div>
      ))}
    </div>
  );
}

export function toggleSelected(selectedVideos: Set<string>, videoId: string) {
  const next = new Set(selectedVideos);
  if (next.has(videoId)) next.delete(videoId);
  else next.add(videoId);
  return next;
}

export function hasCanvasVideo(canvas: CanvasDocument | null) {
  return Boolean(canvas?.sections.some((section) => section.blocks.some((block) => block.type === "video")));
}
