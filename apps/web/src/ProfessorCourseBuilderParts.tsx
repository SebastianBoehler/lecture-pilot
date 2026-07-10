import { useI18n } from "./i18n";
import type { CourseSetup } from "./professorBuilderState";
import type { YoutubeCandidateGroup } from "./professorYoutubeSuggestions";
import type { CanvasDocument, SourceBundleManifest, YoutubeVideoCandidate } from "./types";

export function StepHeader({
  number,
  title,
  done,
}: {
  number: string;
  title: string;
  done: boolean;
}) {
  const { t } = useI18n();
  return (
    <header className="step-header">
      <h2>{title}</h2>
      <strong>{done ? t("builder.status.ready") : t("builder.status.pending")}</strong>
      <span>{number}</span>
    </header>
  );
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
  const { t } = useI18n();
  return (
    <section className="flow-card wide">
      <StepHeader number="01" title={t("builder.define.title")} done={courseReady} />
      <label>
        {t("builder.define.courseName")}
        <input
          value={setup.courseTitle}
          onChange={(event) => onSetupChange({ ...setup, courseTitle: event.target.value })}
        />
      </label>
      <label>
        {t("builder.define.visibility")}
        <select
          value={setup.accessPolicy}
          onChange={(event) =>
            onSetupChange({
              ...setup,
              accessPolicy: event.target.value as CourseSetup["accessPolicy"],
            })
          }
        >
          <option value="tuebingen_enrolled">{t("builder.define.visibility.enrolled")}</option>
          <option value="platform_authenticated">
            {t("builder.define.visibility.university")}
          </option>
          <option value="public">{t("builder.define.visibility.public")}</option>
        </select>
      </label>
      <div className="scope-toggle" role="group" aria-label={t("builder.define.scope")}>
        <button
          className={setup.target === "single-lecture" ? "is-active" : ""}
          type="button"
          onClick={() => onSetupChange({ ...setup, target: "single-lecture" })}
        >
          {t("builder.define.specificLecture")}
        </button>
        <button
          className={setup.target === "full-course" ? "is-active" : ""}
          type="button"
          onClick={() => onSetupChange({ ...setup, target: "full-course", lectureCount: "" })}
        >
          {t("builder.define.fullCourse")}
        </button>
      </div>
      {setup.target === "single-lecture" ? (
        <div className="flow-grid">
          <label>
            {t("builder.define.lectureNumber")}
            <input
              value={setup.lectureNumber}
              onChange={(event) => onSetupChange({ ...setup, lectureNumber: event.target.value })}
            />
          </label>
          <label>
            {t("builder.define.lectureTitle")}
            <input
              value={setup.lectureTitle}
              onChange={(event) => onSetupChange({ ...setup, lectureTitle: event.target.value })}
            />
          </label>
        </div>
      ) : (
        <div className="flow-grid course-scope-grid">
          <label>
            {t("builder.define.expectedLectures")}
            <input
              min="1"
              placeholder={t("builder.define.inferFromMaterials")}
              type="number"
              value={setup.lectureCount}
              onChange={(event) => onSetupChange({ ...setup, lectureCount: event.target.value })}
            />
          </label>
          <label>
            {t("builder.define.firstLectureDate")}
            <input
              placeholder="YYYY-MM-DD"
              value={setup.firstLectureDate}
              onChange={(event) =>
                onSetupChange({ ...setup, firstLectureDate: event.target.value })
              }
            />
          </label>
        </div>
      )}
      <button
        className="primary-action"
        disabled={!isReady || isCreating}
        type="button"
        onClick={onCreate}
      >
        {isCreating ? t("builder.define.creating") : t("builder.define.create")}
      </button>
      {isCreating ? <PendingStatus label={t("builder.define.creatingStatus")} /> : null}
    </section>
  );
}

export function BundleSummary({ bundle }: { bundle: SourceBundleManifest }) {
  const { t } = useI18n();
  if (!bundle.files.length) return <p>{t("builder.upload.noMaterials")}</p>;
  const breakdown = bundleBreakdown(bundle, {
    images: t("builder.upload.images"),
    notebooks: t("builder.upload.notebooks"),
    textFiles: t("builder.upload.textFiles"),
    videos: t("builder.upload.videos"),
  });
  return (
    <section className="bundle-summary" aria-live="polite">
      <strong>{t("builder.upload.filesIndexed", { count: bundle.files.length })}</strong>
      {breakdown.sources.length ? (
        <span>
          {t("builder.upload.sources")} · {breakdown.sources.join(" · ")}
        </span>
      ) : null}
      {breakdown.media.length ? (
        <span>
          {t("builder.upload.media")} · {breakdown.media.join(" · ")}
        </span>
      ) : null}
      {breakdown.other ? (
        <small>{t("builder.upload.other", { count: breakdown.other })}</small>
      ) : null}
    </section>
  );
}

function bundleBreakdown(
  bundle: SourceBundleManifest,
  labels: { images: string; notebooks: string; textFiles: string; videos: string },
) {
  const counts = bundle.counts_by_kind;
  const sources = [
    materialCount(counts, "pdf", "PDF"),
    materialCount(counts, "latex", "LaTeX"),
    materialCount(counts, "markdown", "Markdown"),
    materialCount(counts, "notebook", labels.notebooks),
    materialCount(counts, "text", labels.textFiles),
  ].filter(Boolean);
  const media = [
    materialCount(counts, "image", labels.images),
    materialCount(counts, "video", labels.videos),
  ].filter(Boolean);
  const represented = ["pdf", "latex", "markdown", "notebook", "text", "image", "video"]
    .map((kind) => counts[kind] ?? 0)
    .reduce((total, count) => total + count, 0);
  return { media, other: Math.max(0, bundle.files.length - represented), sources };
}

function materialCount(counts: Record<string, number>, kind: string, label: string) {
  const count = counts[kind] ?? 0;
  return count ? `${count} ${label}` : null;
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
  const { t } = useI18n();
  if (!groups.length) return null;
  return (
    <div className="video-candidate-groups">
      {groups.map((group) => (
        <section className="video-candidate-group" key={group.query}>
          <h3>{group.query}</h3>
          <VideoCandidates
            emptyLabel={t("builder.video.noStrongCandidates")}
            videos={group.videos}
            selectedVideos={selectedVideos}
            onToggle={onToggle}
          />
        </section>
      ))}
    </div>
  );
}

export function VideoCandidates({
  emptyLabel,
  videos,
  selectedVideos,
  onToggle,
}: {
  emptyLabel?: string;
  videos: YoutubeVideoCandidate[];
  selectedVideos: Set<string>;
  onToggle: (videoId: string) => void;
}) {
  const { t } = useI18n();
  if (!videos.length) {
    return <p className="drawer-note">{emptyLabel ?? t("builder.video.noCandidates")}</p>;
  }
  return (
    <div className="video-candidate-list">
      {videos.map((video) => {
        const selected = selectedVideos.has(video.video_id);
        return (
          <div className={`video-candidate${selected ? " is-selected" : ""}`} key={video.video_id}>
            <label className="video-candidate-choice">
              <input checked={selected} onChange={() => onToggle(video.video_id)} type="checkbox" />
              <span className="video-candidate-thumbnail">
                {video.thumbnail_url ? (
                  <img
                    alt={t("builder.video.thumbnailAlt", { title: video.title })}
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    src={video.thumbnail_url}
                  />
                ) : (
                  <span>{t("builder.video.noThumbnail")}</span>
                )}
              </span>
              <span className="video-candidate-copy">
                <strong>{video.title}</strong>
                <span>
                  {video.channel_title} ·{" "}
                  {video.duration.display ?? t("builder.video.durationUnknown")}
                </span>
                <small>{video.reason}</small>
              </span>
            </label>
            <a className="video-preview-link" href={video.url} rel="noreferrer" target="_blank">
              {t("builder.video.open")}
            </a>
          </div>
        );
      })}
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
  return Boolean(
    canvas?.sections.some((section) => section.blocks.some((block) => block.type === "video")),
  );
}
