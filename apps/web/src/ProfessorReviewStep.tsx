import { PendingStatus, StepHeader, VideoCandidateGroups, VideoCandidates } from "./ProfessorCourseBuilderParts";
import type { BuilderAction } from "./professorWorkflowRun";
import type { Lecture, YoutubeVideoCandidate } from "./types";
import type { YoutubeCandidateGroup } from "./professorYoutubeSuggestions";

export function ProfessorReviewStep({
  canInclude,
  canSearch,
  canSuggest,
  canContinue,
  onInclude,
  onContinue,
  onQueryChange,
  onSearch,
  onSuggest,
  onTargetLectureChange,
  onToggleVideo,
  targetLectureId,
  targetLectures,
  pendingAction,
  query,
  ready,
  selectedVideos,
  suggestedGroups,
  suggestedQueries,
  videos,
}: {
  canInclude: boolean;
  canSearch: boolean;
  canSuggest: boolean;
  canContinue: boolean;
  pendingAction: BuilderAction | null;
  onInclude: () => void;
  onContinue: () => void;
  onQueryChange: (query: string) => void;
  onSearch: () => void;
  onSuggest: () => void;
  onTargetLectureChange: (lectureId: string) => void;
  onToggleVideo: (videoId: string) => void;
  query: string;
  ready: boolean;
  selectedVideos: Set<string>;
  suggestedGroups: YoutubeCandidateGroup[];
  suggestedQueries: string[];
  targetLectureId: string;
  targetLectures: Lecture[];
  videos: YoutubeVideoCandidate[];
}) {
  const isBusy = pendingAction !== null;
  const isIncluding = pendingAction === "include-videos";
  const isSearching = pendingAction === "search";
  const isSuggesting = pendingAction === "suggest-videos";
  return (
    <section className="flow-card wide">
      <StepHeader number="03" title="Review YouTube candidates" done={ready} />
      <p className="drawer-note">
        Search candidates before canvas generation. Selected videos are saved to the selected lecture workspace and
        included only in that lecture draft.
      </p>
      {targetLectures.length > 1 ? (
        <label>
          Attach selected videos to
          <select
            disabled={isBusy}
            value={targetLectureId}
            onChange={(event) => onTargetLectureChange(event.target.value)}
          >
            {targetLectures.map((lecture) => (
              <option key={lecture.id} value={lecture.id}>
                {lecture.number} · {lecture.title}
              </option>
            ))}
          </select>
        </label>
      ) : targetLectures[0] ? (
        <p className="drawer-note">
          Selected videos attach to lecture {targetLectures[0].number}: {targetLectures[0].title}.
        </p>
      ) : null}
      <section className="youtube-suggestion-plan" aria-label="Suggested YouTube searches">
        <div>
          <strong>Suggested searches</strong>
          <p>Run a few course-aware searches, then approve only the videos that fit the lecture material.</p>
        </div>
        <div className="youtube-query-list">
          {suggestedQueries.map((suggestion) => <span key={suggestion}>{suggestion}</span>)}
        </div>
        <button disabled={!canSuggest || isBusy} type="button" onClick={onSuggest}>
          {isSuggesting ? "Finding suggestions..." : "Find suggested videos"}
        </button>
      </section>
      {isSuggesting ? <PendingStatus label="Searching suggested YouTube candidates..." /> : null}
      <VideoCandidateGroups groups={suggestedGroups} selectedVideos={selectedVideos} onToggle={onToggleVideo} />
      <label>
        Search query
        <input disabled={isBusy} value={query} onChange={(event) => onQueryChange(event.target.value)} />
      </label>
      <button disabled={!canSearch || isBusy} type="button" onClick={onSearch}>
        {isSearching ? "Searching YouTube..." : "Search YouTube"}
      </button>
      {isSearching ? <PendingStatus label="Searching YouTube candidates..." /> : null}
      <VideoCandidates emptyLabel={suggestedGroups.length ? "No custom search run yet." : undefined} videos={videos} selectedVideos={selectedVideos} onToggle={onToggleVideo} />
      <button disabled={!canInclude || isBusy} type="button" onClick={onInclude}>
        {isIncluding ? "Including selected videos..." : "Include selected videos"}
      </button>
      <button className="primary-action" disabled={!canContinue || isBusy} type="button" onClick={onContinue}>
        Continue to canvas draft
      </button>
      {isIncluding ? <PendingStatus label="Saving selected videos for the canvas draft..." /> : null}
    </section>
  );
}
