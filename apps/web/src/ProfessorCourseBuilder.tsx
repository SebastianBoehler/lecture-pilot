import { useEffect, useState } from "react";
import { draftLectureCanvas, getDraftLectureCanvas } from "./api";
import { builderSteps, initialBuilderStep, ProfessorBuilderStepper, type BuilderStep } from "./ProfessorBuilderStepper";
import { ProfessorCanvasDraftStep } from "./ProfessorCanvasDraftStep";
import { CourseSetupStep, hasCanvasVideo, toggleSelected } from "./ProfessorCourseBuilderParts";
import { ProfessorMaterialStep } from "./ProfessorMaterialStep";
import { ProfessorPublishStep } from "./ProfessorPublishStep";
import { ProfessorReviewStep } from "./ProfessorReviewStep";
import {
  createCourseWorkspace,
  getSourceBundle,
  includeYoutubeMedia,
  proposeLectureSchedule,
  searchYoutubeMedia,
  uploadCourseMaterial,
} from "./professorApi";
import { isCourseSetupReady, readSavedFlow, writeSavedFlow } from "./professorBuilderState";
import { useProfessorWorkflowRun } from "./professorWorkflowRun";
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
  const [activeStep, setActiveStep] = useState<BuilderStep>(() => initialBuilderStep({
    bundleReady: savedFlow.bundleReady,
    canvasReady: savedFlow.canvasReady,
    courseReady: savedFlow.courseReady && Boolean(savedFlow.workspace),
  }));
  const [bundle, setBundle] = useState<SourceBundleManifest | null>(null);
  const [lectureSchedule, setLectureSchedule] = useState<LectureScheduleItem[]>(savedFlow.lectureSchedule);
  const [uploadPath, setUploadPath] = useState(savedFlow.uploadPath);
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [canvas, setCanvas] = useState<CanvasDocument | null>(null);
  const [query, setQuery] = useState(savedFlow.query);
  const [videos, setVideos] = useState<YoutubeVideoCandidate[]>([]);
  const [selectedVideos, setSelectedVideos] = useState<Set<string>>(new Set());
  const { error, notice, pendingAction, run, setError } = useProfessorWorkflowRun();
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
  const steps = builderSteps({
    bundleReady: Boolean(bundle),
    canvasReady: Boolean(canvas),
    courseReady,
    videoReviewReady,
    workspacePublished,
  });
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
  function updateSetup(nextSetup: CourseSetup) {
    setSetup(nextSetup);
    setWorkspace(null);
    setCourseReady(false);
    setBundle(null);
    setLectureSchedule([]);
    setCanvas(null);
    setVideos([]);
    setSelectedVideos(new Set());
    setActiveStep("define");
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
      <ProfessorBuilderStepper activeStep={activeStep} steps={steps} onStepChange={setActiveStep} />
      <div className="professor-flow">
        {activeStep === "define" ? (
          <CourseSetupStep
            courseReady={courseReady}
            isCreating={pendingAction === "create"}
            isReady={setupReady}
            onCreate={() => run("create", async () => {
              const schedule = setup.target === "full-course" ? lectureSchedule : [];
              const created = await createCourseWorkspace(setup, session, schedule);
              setWorkspace({ courseId: created.course.id, lectureId: created.active_lecture_id });
              setCourseReady(true);
              setActiveStep("upload");
              return `Course workspace ${created.course.id}/${created.active_lecture_id} ready.`;
            })}
            onSetupChange={updateSetup}
            setup={setup}
          />
        ) : null}
        {activeStep === "upload" ? (
          <ProfessorMaterialStep
            bundle={bundle}
            courseReady={courseReady}
            lectureSchedule={lectureSchedule}
            materialScope={materialScope}
            pendingAction={pendingAction}
            setup={setup}
            uploadFiles={uploadFiles}
            uploadPath={uploadPath}
            workspaceReady={Boolean(workspace)}
            setUploadPath={setUploadPath}
            onUploadFilesChange={setUploadFiles}
            onScheduleChange={setLectureSchedule}
            onUpload={() => run("upload", async () => {
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
              if (setup.target !== "full-course") setActiveStep("generate");
              if (uploaded.length === 1) return `Uploaded ${uploaded[0].path} as ${uploaded[0].kind}.`;
              return `Uploaded ${uploaded.length} materials into the source bundle.`;
            })}
            onScan={() => run("scan", async () => {
              const activeWorkspace = requireWorkspace(workspace);
              await updateBundleAndSchedule(activeWorkspace.courseId);
              if (setup.target !== "full-course") setActiveStep("generate");
              return "Source bundle scanned.";
            })}
            onApplySchedule={() => run("apply-schedule", async () => {
              const created = await createCourseWorkspace(setup, session, lectureSchedule);
              setWorkspace({ courseId: created.course.id, lectureId: created.active_lecture_id });
              setActiveStep("generate");
              return `Lecture schedule applied with ${created.lectures.length} dated lectures.`;
            })}
          />
        ) : null}
        {activeStep === "generate" ? (
          <ProfessorCanvasDraftStep
            canvas={canvas}
            canGenerate={Boolean(bundle && workspace)}
            isGenerating={pendingAction === "generate"}
            previewHref={previewHref}
            onGenerate={() => run("generate", async () => {
              const activeWorkspace = requireWorkspace(workspace);
              setCanvas(await draftLectureCanvas(activeWorkspace.courseId, activeWorkspace.lectureId, session));
              setActiveStep("review");
              return "Course-builder agent generated a source-grounded canvas draft.";
            })}
          />
        ) : null}
        {activeStep === "review" ? (
          <ProfessorReviewStep
            canInclude={Boolean(selectedVideos.size && canvas && workspace)}
            canSearch={Boolean(setupReady && workspace)}
            hasCanvas={Boolean(canvas)}
            pendingAction={pendingAction}
            onInclude={() => run("include-videos", async () => {
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
              setCanvas(await getDraftLectureCanvas(activeWorkspace.courseId, activeWorkspace.lectureId, session));
              setActiveStep("publish");
              return `Included ${selected.length} approved video${selected.length === 1 ? "" : "s"} in the canvas.`;
            })}
            onQueryChange={setQuery}
            onSearch={() => run("search", async () => {
              const searchQuery = query.trim() || defaultYoutubeQuery;
              if (!query.trim()) setQuery(searchQuery);
              const activeWorkspace = requireWorkspace(workspace);
              const response = await searchYoutubeMedia(activeWorkspace.courseId, searchQuery, session);
              setVideos(response.items);
              return `Found ${response.items.length} YouTube candidates.`;
            })}
            onToggleVideo={(videoId) => setSelectedVideos(toggleSelected(selectedVideos, videoId))}
            query={query}
            ready={videoReviewReady}
            selectedVideos={selectedVideos}
            videos={videos}
          />
        ) : null}
        {activeStep === "publish" ? (
          <ProfessorPublishStep
            canPublish={Boolean(canvas && workspace)}
            isPublishing={pendingAction === "publish"}
            onPublish={() => run("publish", async () => {
              const activeWorkspace = requireWorkspace(workspace);
              const published = await onPublishWorkspace(activeWorkspace.courseId, activeWorkspace.lectureId);
              const when = published.published_at ? ` at ${new Date(published.published_at).toLocaleString()}` : "";
              return `Tutor workspace published as version ${published.version ?? 1}${when}.`;
            })}
            ready={workspacePublished}
          />
        ) : null}
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
