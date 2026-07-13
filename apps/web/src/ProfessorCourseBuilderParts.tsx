import { useI18n } from "./i18n";
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
