import type { CanvasDocument, SourceBundleManifest, YoutubeVideoCandidate } from "./types";

export function StepHeader({ number, title, done }: { number: string; title: string; done: boolean }) {
  return <header className="step-header"><span>{number}</span><h2>{title}</h2><strong>{done ? "Ready" : "Pending"}</strong></header>;
}

export function BundleSummary({ bundle }: { bundle: SourceBundleManifest }) {
  return <p>{bundle.files.length} files indexed · {Object.entries(bundle.counts_by_kind).map(([kind, count]) => `${count} ${kind}`).join(", ")}</p>;
}

export function VideoCandidates({ videos, selectedVideos, onToggle }: {
  videos: YoutubeVideoCandidate[];
  selectedVideos: Set<string>;
  onToggle: (videoId: string) => void;
}) {
  if (!videos.length) return <p className="drawer-note">No candidates searched yet.</p>;
  return (
    <div className="video-candidate-list">
      {videos.map((video) => (
        <label className="video-candidate" key={video.video_id}>
          <input
            checked={selectedVideos.has(video.video_id)}
            onChange={() => onToggle(video.video_id)}
            type="checkbox"
          />
          <span><strong>{video.title}</strong>{video.channel_title} · {video.duration.display ?? "duration unknown"}</span>
        </label>
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
