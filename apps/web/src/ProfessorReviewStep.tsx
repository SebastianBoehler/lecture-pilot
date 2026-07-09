import { useI18n } from "./i18n";
import {
  PendingStatus,
  StepHeader,
  VideoCandidateGroups,
  VideoCandidates,
} from "./ProfessorCourseBuilderParts";
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
  const { t } = useI18n();
  const isBusy = pendingAction !== null;
  const isIncluding = pendingAction === "include-videos";
  const isSearching = pendingAction === "search";
  const isSuggesting = pendingAction === "suggest-videos";
  return (
    <section className="flow-card wide">
      <StepHeader number="03" title={t("builder.review.title")} done={ready} />
      <p className="drawer-note">{t("builder.review.help")}</p>
      {targetLectures.length > 1 ? (
        <label>
          {t("builder.review.attachTo")}
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
          {t("builder.review.attachSingle", {
            number: targetLectures[0].number,
            title: targetLectures[0].title,
          })}
        </p>
      ) : null}
      <section
        className="youtube-suggestion-plan"
        aria-label={t("builder.review.suggestedSearches")}
      >
        <div>
          <strong>{t("builder.review.suggestedSearches")}</strong>
          <p>{t("builder.review.suggestedHelp")}</p>
        </div>
        <div className="youtube-query-list">
          {suggestedQueries.map((suggestion) => (
            <span key={suggestion}>{suggestion}</span>
          ))}
        </div>
        <button disabled={!canSuggest || isBusy} type="button" onClick={onSuggest}>
          {isSuggesting
            ? t("builder.review.finding")
            : suggestedGroups.length
              ? t("builder.review.refresh")
              : t("builder.review.find")}
        </button>
      </section>
      {isSuggesting ? <PendingStatus label={t("builder.review.searchingSuggested")} /> : null}
      <VideoCandidateGroups
        groups={suggestedGroups}
        selectedVideos={selectedVideos}
        onToggle={onToggleVideo}
      />
      <label>
        {t("builder.review.searchQuery")}
        <input
          disabled={isBusy}
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
        />
      </label>
      <button disabled={!canSearch || isBusy} type="button" onClick={onSearch}>
        {isSearching ? t("builder.review.searchingYoutube") : t("builder.review.searchYoutube")}
      </button>
      {isSearching ? <PendingStatus label={t("builder.review.searchingYoutube")} /> : null}
      <VideoCandidates
        emptyLabel={suggestedGroups.length ? t("builder.review.noCustomSearch") : undefined}
        videos={videos}
        selectedVideos={selectedVideos}
        onToggle={onToggleVideo}
      />
      <button disabled={!canInclude || isBusy} type="button" onClick={onInclude}>
        {isIncluding ? t("builder.review.including") : t("builder.review.include")}
      </button>
      <button
        className="primary-action"
        disabled={!canContinue || isBusy}
        type="button"
        onClick={onContinue}
      >
        {t("builder.review.continue")}
      </button>
      {isIncluding ? <PendingStatus label={t("builder.review.saving")} /> : null}
    </section>
  );
}
