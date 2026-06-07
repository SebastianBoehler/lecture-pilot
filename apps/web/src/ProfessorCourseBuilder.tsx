import { FormEvent, useState } from "react";

import {
  getLectureCanvas,
  getSourceBundle,
  includeYoutubeMedia,
  searchYoutubeMedia,
  uploadCourseMaterial,
} from "./api";
import type { CanvasDocument, SourceBundleManifest, YoutubeVideoCandidate } from "./types";

const courseId = "martius-ml";
const lectureId = "lecture-03";

export function ProfessorCourseBuilder({ onBack }: { onBack: () => void }) {
  const [profile, setProfile] = useState({ name: "Prof. Georg Martius", email: "prof@uni-tuebingen.de" });
  const [accountReady, setAccountReady] = useState(false);
  const [courseReady, setCourseReady] = useState(false);
  const [bundle, setBundle] = useState<SourceBundleManifest | null>(null);
  const [uploadPath, setUploadPath] = useState("uploads/supplement.md");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [canvas, setCanvas] = useState<CanvasDocument | null>(null);
  const [query, setQuery] = useState("Bayesian decision theory machine learning Tübingen");
  const [videos, setVideos] = useState<YoutubeVideoCandidate[]>([]);
  const [selectedVideos, setSelectedVideos] = useState<Set<string>>(new Set());
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(action: () => Promise<string | void>) {
    setError(null);
    setNotice(null);
    try {
      const message = await action();
      if (message) setNotice(message);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Professor workflow step failed.");
    }
  }

  function createAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAccountReady(true);
    setNotice("Professor account ready for tenant-tuebingen.");
  }

  return (
    <main className="professor-screen">
      <section className="dashboard-header">
        <button className="ghost-button" type="button" onClick={onBack}>Back</button>
        <p className="section-label">Professor workspace</p>
        <h1>Course creation flow</h1>
        <p>Register, upload material, draft the canvas, then approve YouTube media.</p>
      </section>

      <div className="professor-flow">
        <form className="flow-card" onSubmit={createAccount}>
          <StepHeader number="01" title="Professor sign up" done={accountReady} />
          <label>
            Name
            <input value={profile.name} onChange={(event) => setProfile({ ...profile, name: event.target.value })} />
          </label>
          <label>
            Email
            <input value={profile.email} onChange={(event) => setProfile({ ...profile, email: event.target.value })} />
          </label>
          <button type="submit">Create professor account</button>
        </form>

        <section className="flow-card">
          <StepHeader number="02" title="Create course workspace" done={courseReady} />
          <dl className="flow-facts">
            <div><dt>Course</dt><dd>Grundlagen des Maschinellen Lernens</dd></div>
            <div><dt>Lecture draft</dt><dd>Lecture 03 · Bayesian Decision Theory</dd></div>
          </dl>
          <button disabled={!accountReady} type="button" onClick={() => setCourseReady(true)}>
            Create course workspace
          </button>
        </section>

        <section className="flow-card">
          <StepHeader number="03" title="Upload and scan materials" done={Boolean(bundle)} />
          <label>
            Workspace path
            <input value={uploadPath} onChange={(event) => setUploadPath(event.target.value)} />
          </label>
          <input
            aria-label="Upload course material"
            disabled={!courseReady}
            onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
            type="file"
          />
          <div className="flow-actions">
            <button
              disabled={!courseReady || !uploadFile}
              type="button"
              onClick={() => run(async () => {
                if (!uploadFile) return;
                const result = await uploadCourseMaterial({ courseId, path: uploadPath, file: uploadFile });
                return `Uploaded ${result.path} as ${result.kind}.`;
              })}
            >
              Upload material
            </button>
            <button disabled={!courseReady} type="button" onClick={() => run(async () => {
              setBundle(await getSourceBundle(courseId));
              return "Source bundle scanned.";
            })}>
              Scan source bundle
            </button>
          </div>
          {bundle ? <BundleSummary bundle={bundle} /> : null}
        </section>

        <section className="flow-card">
          <StepHeader number="04" title="Generate canvas draft" done={Boolean(canvas)} />
          <button disabled={!bundle} type="button" onClick={() => run(async () => {
            setCanvas(await getLectureCanvas(courseId, lectureId, "professor-preview"));
            return "Canvas draft generated from course materials.";
          })}>
            Generate draft canvas
          </button>
          {canvas ? <p>{canvas.sections.length} sections ready for review.</p> : null}
        </section>

        <section className="flow-card wide">
          <StepHeader number="05" title="Review YouTube candidates" done={selectedVideos.size > 0} />
          <label>
            Search query
            <input value={query} onChange={(event) => setQuery(event.target.value)} />
          </label>
          <button disabled={!canvas} type="button" onClick={() => run(async () => {
            const response = await searchYoutubeMedia(courseId, query);
            setVideos(response.items);
            return `Found ${response.items.length} YouTube candidates.`;
          })}>
            Search YouTube
          </button>
          <VideoCandidates
            videos={videos}
            selectedVideos={selectedVideos}
            onToggle={(videoId) => setSelectedVideos(toggleSelected(selectedVideos, videoId))}
          />
          <button disabled={!selectedVideos.size || !canvas} type="button" onClick={() => run(async () => {
            const selected = videos.filter((video) => selectedVideos.has(video.video_id));
            for (const video of selected) {
              await includeYoutubeMedia({ courseId, lectureId, sectionId: canvas?.sections[1]?.id ?? null, video });
            }
            setCanvas(await getLectureCanvas(courseId, lectureId, "professor-preview"));
            return `Included ${selected.length} approved video${selected.length === 1 ? "" : "s"} in the canvas.`;
          })}>
            Include selected videos
          </button>
        </section>
      </div>
      {notice ? <p className="form-success">{notice}</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
    </main>
  );
}

function StepHeader({ number, title, done }: { number: string; title: string; done: boolean }) {
  return <header className="step-header"><span>{number}</span><h2>{title}</h2><strong>{done ? "Ready" : "Pending"}</strong></header>;
}

function BundleSummary({ bundle }: { bundle: SourceBundleManifest }) {
  return <p>{bundle.files.length} files indexed · {Object.entries(bundle.counts_by_kind).map(([kind, count]) => `${count} ${kind}`).join(", ")}</p>;
}

function VideoCandidates({ videos, selectedVideos, onToggle }: {
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

function toggleSelected(selectedVideos: Set<string>, videoId: string) {
  const next = new Set(selectedVideos);
  if (next.has(videoId)) next.delete(videoId);
  else next.add(videoId);
  return next;
}
