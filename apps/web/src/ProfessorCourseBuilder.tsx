import { useEffect, useState } from "react";
import {
  clearCourseYoutubeMedia,
  createCourseWorkspace,
  draftLectureCanvas,
  getLectureCanvas,
  getSourceBundle,
  includeYoutubeMedia,
  searchYoutubeMedia,
  uploadCourseMaterial,
} from "./api";
import {
  BundleSummary,
  CourseSetupStep,
  hasCanvasVideo,
  StepHeader,
  toggleSelected,
  VideoCandidates,
} from "./ProfessorCourseBuilderParts";
import { defaultFlow, isCourseSetupReady, readSavedFlow, writeSavedFlow } from "./professorBuilderState";
import { lectureFromWorkspace, requireWorkspace } from "./professorWorkspaceView";
import { uploadDestination } from "./professorUpload";
import type { CanvasDocument, LoginSession, SourceBundleManifest, YoutubeVideoCandidate } from "./types";
import type { CourseSetup } from "./professorBuilderState";
export function ProfessorCourseBuilder({
  session,
  onBack,
  onPublishWorkspace,
  onResetWorkspace,
  onPreviewWorkspace,
  workspacePublished,
}: {
  session: LoginSession;
  onBack: () => void;
  onPublishWorkspace: () => void;
  onResetWorkspace: () => void;
  onPreviewWorkspace: (courseId: string, lecture: ReturnType<typeof lectureFromWorkspace>) => void;
  workspacePublished: boolean;
}) {
  const [savedFlow] = useState(readSavedFlow);
  const [setup, setSetup] = useState(savedFlow.setup);
  const [workspace, setWorkspace] = useState(savedFlow.workspace);
  const [courseReady, setCourseReady] = useState(savedFlow.courseReady && Boolean(savedFlow.workspace));
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
  const setupReady = isCourseSetupReady(setup);
  const materialScope = setup.target === "full-course" ? "all course materials" : "materials for this lecture";
  const defaultYoutubeQuery = [
    setup.courseTitle,
    setup.target === "single-lecture" ? setup.lectureTitle : "machine learning lecture",
  ].filter(Boolean).join(" ");
  useEffect(() => {
    let cancelled = false;
    async function restoreGeneratedState() {
      try {
        if (savedFlow.bundleReady && savedFlow.workspace) {
          const restoredBundle = await getSourceBundle(savedFlow.workspace.courseId, session);
          if (!cancelled) setBundle(restoredBundle);
        }
        if ((savedFlow.bundleReady || savedFlow.canvasReady) && savedFlow.workspace) {
          try {
            const restoredCanvas = await getLectureCanvas(
              savedFlow.workspace.courseId,
              savedFlow.workspace.lectureId,
              "professor-preview",
              session,
            );
            if (!cancelled) setCanvas(restoredCanvas);
          } catch (canvasError) {
            if (savedFlow.canvasReady && !cancelled) {
              setError(canvasError instanceof Error ? canvasError.message : "Could not restore professor preview.");
            }
          }
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
      setup,
      workspace,
      courseReady,
      uploadPath,
      bundleReady: Boolean(bundle),
      canvasReady: Boolean(canvas),
      query,
    });
  }, [bundle, canvas, courseReady, query, restored, setup, uploadPath, workspace]);
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
  async function resetFlow() {
    const activeWorkspace = workspace;
    setSetup(defaultFlow.setup);
    setWorkspace(null);
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
      if (activeWorkspace) await clearCourseYoutubeMedia(activeWorkspace.courseId, session);
      return "Professor flow reset.";
    });
  }
  function updateSetup(nextSetup: CourseSetup) {
    setSetup(nextSetup);
    setWorkspace(null);
    setCourseReady(false);
    setBundle(null);
    setCanvas(null);
    setVideos([]);
    setSelectedVideos(new Set());
  }
  return (
    <main className="professor-screen">
      <section className="dashboard-header">
        <button className="ghost-button" type="button" onClick={onBack}>Back</button>
        <button className="ghost-button" type="button" onClick={() => void resetFlow()}>Reset flow</button>
        <p className="section-label">Professor workspace</p>
        <h1>Course creation flow</h1>
        <p>Signed in as {session.username}. Define the course scope, upload material, draft the canvas, then approve media.</p>
      </section>
      <div className="professor-flow">
        <CourseSetupStep
          courseReady={courseReady}
          isReady={setupReady}
          onCreate={() => run(async () => {
            const created = await createCourseWorkspace(setup, session);
            setWorkspace({
              courseId: created.course.id,
              lectureId: created.active_lecture_id,
            });
            setCourseReady(true);
            return `Course workspace ${created.course.id}/${created.active_lecture_id} ready.`;
          })}
          onSetupChange={updateSetup}
          setup={setup}
        />
        <section className="flow-card">
          <StepHeader number="02" title="Upload and scan materials" done={Boolean(bundle)} />
          <p className="drawer-note">Upload {materialScope} for {setup.courseTitle}.</p>
          <label>
            Store uploaded files under
            <input value={uploadPath} onChange={(event) => setUploadPath(event.target.value)} />
          </label>
          <input
            aria-label="Upload course material"
            disabled={!courseReady || !workspace}
            multiple
            onChange={(event) => setUploadFiles(Array.from(event.target.files ?? []))}
            type="file"
            {...{ directory: "", webkitdirectory: "" }}
          />
          <div className="flow-actions">
            <button
              disabled={!courseReady || !workspace || !uploadFiles.length}
              type="button"
              onClick={() => run(async () => {
                const activeWorkspace = requireWorkspace(workspace);
                const uploaded = [];
                for (const file of uploadFiles) {
                  uploaded.push(await uploadCourseMaterial({
                    courseId: activeWorkspace.courseId,
                    path: uploadDestination(uploadPath, file, uploadFiles.length),
                    file,
                    session,
                  }));
                }
                setBundle(await getSourceBundle(activeWorkspace.courseId, session));
                if (uploaded.length === 1) return `Uploaded ${uploaded[0].path} as ${uploaded[0].kind}.`;
                return `Uploaded ${uploaded.length} materials into the source bundle.`;
              })}
            >
              Upload material
            </button>
            <button disabled={!courseReady || !workspace} type="button" onClick={() => run(async () => {
              const activeWorkspace = requireWorkspace(workspace);
              setBundle(await getSourceBundle(activeWorkspace.courseId, session));
              return "Source bundle scanned.";
            })}>
              Scan source bundle
            </button>
          </div>
          {bundle ? <BundleSummary bundle={bundle} /> : null}
        </section>
        <section className="flow-card">
          <StepHeader number="03" title="Generate canvas draft" done={Boolean(canvas)} />
          <button disabled={!bundle || !workspace} type="button" onClick={() => run(async () => {
            const activeWorkspace = requireWorkspace(workspace);
            setCanvas(await draftLectureCanvas(activeWorkspace.courseId, activeWorkspace.lectureId, session));
            return "Course-builder agent generated a source-grounded canvas draft.";
          })}>
            Generate draft canvas
          </button>
          {canvas ? <p>{canvas.sections.length} sections ready for review.</p> : null}
          <button disabled={!canvas || !workspace} type="button" onClick={() => {
            const activeWorkspace = requireWorkspace(workspace);
            onPreviewWorkspace(activeWorkspace.courseId, lectureFromWorkspace(activeWorkspace, setup));
          }}>
            Preview course workspace
          </button>
        </section>
        <section className="flow-card wide">
          <StepHeader number="04" title="Review YouTube candidates" done={videoReviewReady} />
          <p className="drawer-note">
            Search candidates as soon as the course scope is known. Selected videos can be attached after a canvas draft exists.
          </p>
          <label>
            Search query
            <input value={query} onChange={(event) => setQuery(event.target.value)} />
          </label>
          <button disabled={!setupReady || !workspace} type="button" onClick={() => run(async () => {
            const searchQuery = query.trim() || defaultYoutubeQuery;
            if (!query.trim()) setQuery(searchQuery);
            const activeWorkspace = requireWorkspace(workspace);
            const response = await searchYoutubeMedia(activeWorkspace.courseId, searchQuery, session);
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
          <button disabled={!selectedVideos.size || !canvas || !workspace} type="button" onClick={() => run(async () => {
            const activeWorkspace = requireWorkspace(workspace);
            const selected = videos.filter((video) => selectedVideos.has(video.video_id));
            for (const video of selected) {
              await includeYoutubeMedia({
                courseId: activeWorkspace.courseId,
                lectureId: activeWorkspace.lectureId,
                sectionId: canvas?.sections[1]?.id ?? null,
                video,
                session,
              });
            }
            setCanvas(await getLectureCanvas(
              activeWorkspace.courseId,
              activeWorkspace.lectureId,
              "professor-preview",
              session,
            ));
            return `Included ${selected.length} approved video${selected.length === 1 ? "" : "s"} in the canvas.`;
          })}>
            Include selected videos
          </button>
          {!canvas && selectedVideos.size ? (
            <p className="drawer-note">Generate a canvas draft before attaching the selected videos.</p>
          ) : null}
        </section>
        <section className="flow-card wide">
          <StepHeader number="05" title="Publish tutor workspace" done={workspacePublished} />
          <p className="drawer-note">Student dashboards show the AI tutor only after this course workspace is published.</p>
          <button disabled={!canvas || !workspace} type="button" onClick={() => {
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
