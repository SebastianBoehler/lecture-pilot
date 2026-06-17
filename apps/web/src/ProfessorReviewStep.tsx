import { PendingStatus, StepHeader, VideoCandidates } from "./ProfessorCourseBuilderParts";
import type { BuilderAction } from "./professorWorkflowRun";
import type { YoutubeVideoCandidate } from "./types";

export function ProfessorReviewStep({
  canInclude,
  canSearch,
  canContinue,
  onInclude,
  onContinue,
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
  canContinue: boolean;
  pendingAction: BuilderAction | null;
  onInclude: () => void;
  onContinue: () => void;
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
      <StepHeader number="03" title="Review YouTube candidates" done={ready} />
      <p className="drawer-note">
        Search candidates before canvas generation. Selected videos are saved to the course media workspace and
        included in the draft.
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
      <button disabled={!canContinue || isBusy} type="button" onClick={onContinue}>
        Continue to canvas draft
      </button>
      {isIncluding ? <PendingStatus label="Saving selected videos for the canvas draft..." /> : null}
    </section>
  );
}
