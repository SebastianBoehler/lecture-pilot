import { useEffect, useState } from "react";
import { draftLectureCanvas, getDraftLectureCanvas } from "./api";
import { ProfessorCanvasDraftStep } from "./ProfessorCanvasDraftStep";
import {
  CourseSetupStep,
  hasCanvasVideo,
  StepHeader,
  toggleSelected,
  VideoCandidates,
} from "./ProfessorCourseBuilderParts";
import { ProfessorMaterialStep } from "./ProfessorMaterialStep";
import {
  createCourseWorkspace,
  getSourceBundle,
  includeYoutubeMedia,
  proposeLectureSchedule,
  searchYoutubeMedia,
  uploadCourseMaterial,
} from "./professorApi";
import { defaultFlow, isCourseSetupReady, readSavedFlow, writeSavedFlow } from "./professorBuilderState";
import { lectureFromWorkspace, requireWorkspace } from "./professorWorkspaceView";
import { uploadDestination } from "./professorUpload";
import type {
  CanvasDocument,
  CanvasPublicationResult,
  LectureScheduleItem,
  LoginSession,
  SourceBundleManifest,
  YoutubeVideoCandidate,
} from "./types";
import type { CourseSetup } from "./professorBuilderState";
export function ProfessorCourseBuilder({
  session,
  onPublishWorkspace,
  previewWorkspaceUrl,
  publishedLectureIds,
}: {
  session: LoginSession;
  onPublishWorkspace: (courseId: string, lectureId: string) => Promise<CanvasPublicationResult>;
  previewWorkspaceUrl: (courseId: string, lecture: ReturnType<typeof lectureFromWorkspace>) => string;
  publishedLectureIds: string[];
}) {
  const [savedFlow] = useState(readSavedFlow);
  const [setup, setSetup] = useState(savedFlow.setup);
  const [workspace, setWorkspace] = useState(savedFlow.workspace);
  const [courseReady, setCourseReady] = useState(savedFlow.courseReady && Boolean(savedFlow.workspace));
  const [bundle, setBundle] = useState<SourceBundleManifest | null>(null);
  const [lectureSchedule, setLectureSchedule] = useState<LectureScheduleItem[]>(savedFlow.lectureSchedule);
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
  const workspacePublished = Boolean(workspace && publishedLectureIds.includes(workspace.lectureId));
  const previewHref = canvas && workspace
    ? previewWorkspaceUrl(workspace.courseId, lectureFromWorkspace(workspace, setup, lectureSchedule))
    : null;
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
            const restoredCanvas = await getDraftLectureCanvas(
              savedFlow.workspace.courseId,
              savedFlow.workspace.lectureId,
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
      lectureSchedule,
      query,
    });
  }, [bundle, canvas, courseReady, lectureSchedule, query, restored, setup, uploadPath, workspace]);
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
  function updateSetup(nextSetup: CourseSetup) {
    setSetup(nextSetup);
    setWorkspace(null);
    setCourseReady(false);
    setBundle(null);
    setLectureSchedule([]);
    setCanvas(null);
    setVideos([]);
    setSelectedVideos(new Set());
  }
  return (
    <main className="professor-screen">
      <section className="professor-page-header">
        <div>
          <h1>Course builder</h1>
          <p>Define the course scope, upload material, draft the canvas, approve media, then publish for students.</p>
        </div>
        <p className="professor-session">Signed in as {session.username}</p>
      </section>
      <ol className="flow-stepper" aria-label="Course builder progress">
        <li className={courseReady ? "is-ready" : "is-current"}><span>01</span>Define</li>
        <li className={bundle ? "is-ready" : courseReady ? "is-current" : ""}><span>02</span>Upload</li>
        <li className={canvas ? "is-ready" : bundle ? "is-current" : ""}><span>03</span>Generate</li>
        <li className={videoReviewReady ? "is-ready" : canvas ? "is-current" : ""}><span>04</span>Review</li>
        <li className={workspacePublished ? "is-ready" : videoReviewReady ? "is-current" : ""}><span>05</span>Publish</li>
      </ol>
      <div className="professor-flow">
        <CourseSetupStep
          courseReady={courseReady}
          isReady={setupReady}
          onCreate={() => run(async () => {
            const created = await createCourseWorkspace(setup, session, scheduleForSetup(setup, lectureSchedule));
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
        <ProfessorMaterialStep
          bundle={bundle}
          courseReady={courseReady}
          lectureSchedule={lectureSchedule}
          materialScope={materialScope}
          setup={setup}
          uploadFiles={uploadFiles}
          uploadPath={uploadPath}
          workspaceReady={Boolean(workspace)}
          setUploadPath={setUploadPath}
          onUploadFilesChange={setUploadFiles}
          onScheduleChange={setLectureSchedule}
          onUpload={() => run(async () => {
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
            await updateBundleAndSchedule(activeWorkspace.courseId);
            if (uploaded.length === 1) return `Uploaded ${uploaded[0].path} as ${uploaded[0].kind}.`;
            return `Uploaded ${uploaded.length} materials into the source bundle.`;
          })}
          onScan={() => run(async () => {
            const activeWorkspace = requireWorkspace(workspace);
            await updateBundleAndSchedule(activeWorkspace.courseId);
            return "Source bundle scanned.";
          })}
          onApplySchedule={() => run(async () => {
            const created = await createCourseWorkspace(setup, session, lectureSchedule);
            setWorkspace({ courseId: created.course.id, lectureId: created.active_lecture_id });
            return `Lecture schedule applied with ${created.lectures.length} dated lectures.`;
          })}
        />
        <ProfessorCanvasDraftStep
          canvas={canvas}
          canGenerate={Boolean(bundle && workspace)}
          previewHref={previewHref}
          onGenerate={() => run(async () => {
            const activeWorkspace = requireWorkspace(workspace);
            setCanvas(await draftLectureCanvas(activeWorkspace.courseId, activeWorkspace.lectureId, session));
            return "Course-builder agent generated a source-grounded canvas draft.";
          })}
        />
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
            setCanvas(await getDraftLectureCanvas(
              activeWorkspace.courseId,
              activeWorkspace.lectureId,
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
          <button disabled={!canvas || !workspace} type="button" onClick={() => run(async () => {
            const activeWorkspace = requireWorkspace(workspace);
            const published = await onPublishWorkspace(activeWorkspace.courseId, activeWorkspace.lectureId);
            const when = published.published_at ? ` at ${new Date(published.published_at).toLocaleString()}` : "";
            return `Tutor workspace published as version ${published.version ?? 1}${when}.`;
          })}>
            Publish tutor workspace
          </button>
        </section>
      </div>
      {notice ? <p className="form-success">{notice}</p> : null}
      {error ? <p className="form-error">{error}</p> : null}
    </main>
  );

  async function updateBundleAndSchedule(courseId: string) {
    const nextBundle = await getSourceBundle(courseId, session);
    setBundle(nextBundle);
    if (setup.target !== "full-course") return;
    const proposal = await proposeLectureSchedule({
      courseId,
      count: Number(setup.lectureCount) || null,
      firstLectureDate: setup.firstLectureDate,
      session,
    });
    setLectureSchedule(proposal.lectures);
  }
}

function scheduleForSetup(setup: CourseSetup, schedule: LectureScheduleItem[]) {
  return setup.target === "full-course" ? schedule : [];
}
