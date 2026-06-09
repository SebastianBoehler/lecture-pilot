import { FormEvent, useEffect, useState } from "react";

import {
  clearCourseYoutubeMedia,
  draftLectureCanvas,
  getLectureCanvas,
  getSourceBundle,
  includeYoutubeMedia,
  searchYoutubeMedia,
  uploadCourseMaterial,
} from "./api";
import { BundleSummary, hasCanvasVideo, StepHeader, toggleSelected, VideoCandidates } from "./ProfessorCourseBuilderParts";
import { uploadDestination } from "./professorUpload";
import type { CanvasDocument, SourceBundleManifest, YoutubeVideoCandidate } from "./types";

const courseId = "martius-ml";
const lectureId = "lecture-03";
const flowStorageKey = "lecturepilot.professor-builder.martius-ml.lecture-03";
const defaultProfile = { name: "Prof. Georg Martius", email: "prof@uni-tuebingen.de" };

type SavedProfessorFlow = {
  profile: typeof defaultProfile;
  accountReady: boolean;
  courseReady: boolean;
  uploadPath: string;
  bundleReady: boolean;
  canvasReady: boolean;
  query: string;
};

const defaultFlow: SavedProfessorFlow = {
  profile: defaultProfile,
  accountReady: false,
  courseReady: false,
  uploadPath: "uploads/supplement.md",
  bundleReady: false,
  canvasReady: false,
  query: "Bayesian decision theory machine learning Tübingen",
};

export function ProfessorCourseBuilder({
  onBack,
  onPublishWorkspace,
  onResetWorkspace,
  onPreviewWorkspace,
  workspacePublished,
}: {
  onBack: () => void;
  onPublishWorkspace: () => void;
  onResetWorkspace: () => void;
  onPreviewWorkspace: () => void;
  workspacePublished: boolean;
}) {
  const [savedFlow] = useState(readSavedFlow);
  const [profile, setProfile] = useState(savedFlow.profile);
  const [accountReady, setAccountReady] = useState(savedFlow.accountReady);
  const [courseReady, setCourseReady] = useState(savedFlow.courseReady);
  const [bundle, setBundle] = useState<SourceBundleManifest | null>(null);
  const [uploadPath, setUploadPath] = useState(savedFlow.uploadPath);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [canvas, setCanvas] = useState<CanvasDocument | null>(null);
  const [query, setQuery] = useState(savedFlow.query);
  const [videos, setVideos] = useState<YoutubeVideoCandidate[]>([]);
  const [selectedVideos, setSelectedVideos] = useState<Set<string>>(new Set());
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [restored, setRestored] = useState(!savedFlow.bundleReady && !savedFlow.canvasReady);
  const videoReviewReady = selectedVideos.size > 0 || hasCanvasVideo(canvas);

  useEffect(() => {
    let cancelled = false;
    async function restoreGeneratedState() {
      try {
        if (savedFlow.bundleReady) {
          const restoredBundle = await getSourceBundle(courseId);
          if (!cancelled) setBundle(restoredBundle);
        }
        if (savedFlow.canvasReady) {
          const restoredCanvas = await getLectureCanvas(courseId, lectureId, "professor-preview");
          if (!cancelled) setCanvas(restoredCanvas);
        }
      } catch (restoreError) {
        if (!cancelled) {
          setError(restoreError instanceof Error ? restoreError.message : "Could not restore professor preview.");
        }
      } finally {
        if (!cancelled) setRestored(true);
      }
    }
    if (!restored) void restoreGeneratedState();
    return () => {
      cancelled = true;
    };
  }, [restored, savedFlow]);

  useEffect(() => {
    if (!restored) return;
    writeSavedFlow({
      profile,
      accountReady,
      courseReady,
      uploadPath,
      bundleReady: Boolean(bundle),
      canvasReady: Boolean(canvas),
      query,
    });
  }, [accountReady, bundle, canvas, courseReady, profile, query, restored, uploadPath]);

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
  async function resetFlow() {
    setProfile(defaultProfile);
    setAccountReady(false);
    setCourseReady(false);
    setBundle(null);
    setUploadPath(defaultFlow.uploadPath);
    setUploadFiles([]);
    setCanvas(null);
    setVideos([]);
    setSelectedVideos(new Set());
    onResetWorkspace();
    writeSavedFlow(defaultFlow);
    await run(async () => {
      await clearCourseYoutubeMedia(courseId);
      return "Professor flow reset.";
    });
  }

  return (
    <main className="professor-screen">
      <section className="dashboard-header">
        <button className="ghost-button" type="button" onClick={onBack}>Back</button>
        <button className="ghost-button" type="button" onClick={() => void resetFlow()}>Reset flow</button>
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
            multiple
            onChange={(event) => setUploadFiles(Array.from(event.target.files ?? []))}
            type="file"
            {...{ directory: "", webkitdirectory: "" }}
          />
          <div className="flow-actions">
            <button
              disabled={!courseReady || !uploadFiles.length}
              type="button"
              onClick={() => run(async () => {
                const uploaded = [];
                for (const file of uploadFiles) {
                  uploaded.push(await uploadCourseMaterial({
                    courseId,
                    path: uploadDestination(uploadPath, file, uploadFiles.length),
                    file,
                  }));
                }
                setBundle(await getSourceBundle(courseId));
                if (uploaded.length === 1) return `Uploaded ${uploaded[0].path} as ${uploaded[0].kind}.`;
                return `Uploaded ${uploaded.length} materials into the source bundle.`;
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
            setCanvas(await draftLectureCanvas(courseId, lectureId));
            return "Course-builder agent generated a source-grounded canvas draft.";
          })}>
            Generate draft canvas
          </button>
          {canvas ? <p>{canvas.sections.length} sections ready for review.</p> : null}
          <button disabled={!canvas} type="button" onClick={onPreviewWorkspace}>
            Preview course workspace
          </button>
        </section>

        <section className="flow-card wide">
          <StepHeader number="05" title="Review YouTube candidates" done={videoReviewReady} />
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

        <section className="flow-card wide">
          <StepHeader number="06" title="Publish tutor workspace" done={workspacePublished} />
          <p className="drawer-note">Student dashboards show the AI tutor only after this course workspace is published.</p>
          <button disabled={!canvas} type="button" onClick={() => {
            onPublishWorkspace();
            setNotice("Tutor workspace published. Refresh the student dashboard to show AI tutor available.");
          }}>
            Publish tutor workspace
          </button>
        </section>
      </div>
      {notice ? <p className="form-success">{notice}</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
    </main>
  );
}

function readSavedFlow(): SavedProfessorFlow {
  if (typeof window === "undefined") return defaultFlow;
  try {
    const saved = window.sessionStorage.getItem(flowStorageKey);
    if (!saved) return defaultFlow;
    return { ...defaultFlow, ...(JSON.parse(saved) as Partial<SavedProfessorFlow>) };
  } catch {
    return defaultFlow;
  }
}

function writeSavedFlow(flow: SavedProfessorFlow) {
  try {
    window.sessionStorage.setItem(flowStorageKey, JSON.stringify(flow));
  } catch {
  }
}
