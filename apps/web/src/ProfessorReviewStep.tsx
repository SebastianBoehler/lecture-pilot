import { StepHeader, VideoCandidates } from "./ProfessorCourseBuilderParts";
import type { YoutubeVideoCandidate } from "./types";

export function ProfessorReviewStep({
  canInclude,
  canSearch,
  hasCanvas,
  onInclude,
  onQueryChange,
  onSearch,
  onToggleVideo,
  query,
  ready,
  selectedVideos,
  videos,
}: {
  canInclude: boolean;
  canSearch: boolean;
  hasCanvas: boolean;
  onInclude: () => void;
  onQueryChange: (query: string) => void;
  onSearch: () => void;
  onToggleVideo: (videoId: string) => void;
  query: string;
  ready: boolean;
  selectedVideos: Set<string>;
  videos: YoutubeVideoCandidate[];
}) {
  return (
    <section className="flow-card wide">
      <StepHeader number="04" title="Review YouTube candidates" done={ready} />
      <p className="drawer-note">
        Search candidates as soon as the course scope is known. Selected videos can be attached after a canvas draft exists.
      </p>
      <label>
        Search query
        <input value={query} onChange={(event) => onQueryChange(event.target.value)} />
      </label>
      <button disabled={!canSearch} type="button" onClick={onSearch}>
        Search YouTube
      </button>
      <VideoCandidates videos={videos} selectedVideos={selectedVideos} onToggle={onToggleVideo} />
      <button disabled={!canInclude} type="button" onClick={onInclude}>
        Include selected videos
      </button>
      {!hasCanvas && selectedVideos.size ? (
        <p className="drawer-note">Generate a canvas draft before attaching the selected videos.</p>
      ) : null}
    </section>
  );
}
