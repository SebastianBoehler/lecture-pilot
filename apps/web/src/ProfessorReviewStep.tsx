import { PendingStatus, StepHeader, VideoCandidates } from "./ProfessorCourseBuilderParts";
import type { BuilderAction } from "./professorWorkflowRun";
import type { YoutubeVideoCandidate } from "./types";

export function ProfessorReviewStep({
  canInclude,
  canSearch,
  hasCanvas,
  onInclude,
  onQueryChange,
  onSearch,
  onToggleVideo,
  pendingAction,
  query,
  ready,
  selectedVideos,
  videos,
}: {
  canInclude: boolean;
  canSearch: boolean;
  hasCanvas: boolean;
  pendingAction: BuilderAction | null;
  onInclude: () => void;
  onQueryChange: (query: string) => void;
  onSearch: () => void;
  onToggleVideo: (videoId: string) => void;
  query: string;
  ready: boolean;
  selectedVideos: Set<string>;
  videos: YoutubeVideoCandidate[];
}) {
  const isBusy = pendingAction !== null;
  const isIncluding = pendingAction === "include-videos";
  const isSearching = pendingAction === "search";
  return (
    <section className="flow-card wide">
      <StepHeader number="04" title="Review YouTube candidates" done={ready} />
      <p className="drawer-note">
        Search candidates as soon as the course scope is known. Selected videos can be attached after a canvas draft exists.
      </p>
      <label>
        Search query
        <input disabled={isBusy} value={query} onChange={(event) => onQueryChange(event.target.value)} />
      </label>
      <button disabled={!canSearch || isBusy} type="button" onClick={onSearch}>
        {isSearching ? "Searching YouTube..." : "Search YouTube"}
      </button>
      {isSearching ? <PendingStatus label="Searching YouTube candidates..." /> : null}
      <VideoCandidates videos={videos} selectedVideos={selectedVideos} onToggle={onToggleVideo} />
      <button disabled={!canInclude || isBusy} type="button" onClick={onInclude}>
        {isIncluding ? "Including selected videos..." : "Include selected videos"}
      </button>
      {isIncluding ? <PendingStatus label="Attaching selected videos to the canvas draft..." /> : null}
      {!hasCanvas && selectedVideos.size ? (
        <p className="drawer-note">Generate a canvas draft before attaching the selected videos.</p>
      ) : null}
    </section>
  );
}
