import { useEffect, useState } from "react";
import { draftLectureCanvas, getDraftLectureCanvas } from "./api";
import { builderSteps, initialBuilderStep, ProfessorBuilderStepper, type BuilderStep } from "./ProfessorBuilderStepper";
import { ProfessorCanvasDraftStep } from "./ProfessorCanvasDraftStep";
import { generateLectureCanvasDrafts } from "./professorCanvasGeneration";
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
  UniversityCourse,
  YoutubeVideoCandidate,
} from "./types";
import type { CourseSetup } from "./professorBuilderState";
export function ProfessorCourseBuilder({
  session,
  onPublishWorkspace,
  onWorkspaceLecturesChange,
  previewWorkspaceUrl,
  publishedLectureIds,
}: {
  session: LoginSession;
  onPublishWorkspace: (courseId: string, lectureId: string) => Promise<CanvasPublicationResult>;
  onWorkspaceLecturesChange: (course: UniversityCourse, lectures: ReturnType<typeof lectureFromWorkspace>[]) => void;
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
  const [generatedLectureIds, setGeneratedLectureIds] = useState<string[]>([]);
  const [query, setQuery] = useState(savedFlow.query);
  const [videos, setVideos] = useState<YoutubeVideoCandidate[]>([]);
  const [selectedVideos, setSelectedVideos] = useState<Set<string>>(new Set());
  const [mediaIncluded, setMediaIncluded] = useState(false);
  const { error, notice, pendingAction, run, setError } = useProfessorWorkflowRun();
  const [restored, setRestored] = useState(!savedFlow.bundleReady && !savedFlow.canvasReady);
  const mediaReady = mediaIncluded || selectedVideos.size > 0 || hasCanvasVideo(canvas);
  const setupReady = isCourseSetupReady(setup);
  const bundleReady = Boolean(bundle?.files.length);
  const scheduledLectureIds = lectureSchedule.map((lecture) => lectureIdFromNumber(lecture.number));
  const fullCourseLectureIds = setup.target === "full-course" && scheduledLectureIds.length
    ? scheduledLectureIds
    : workspace ? [workspace.lectureId] : [];
  const fullCoursePublishedCount = fullCourseLectureIds.filter((lectureId) => publishedLectureIds.includes(lectureId)).length;
  const materialScope = setup.target === "full-course" ? "all course materials" : "materials for this lecture";
  const defaultYoutubeQuery = [
    setup.courseTitle,
    setup.target === "single-lecture" ? setup.lectureTitle : "machine learning lecture",
  ].filter(Boolean).join(" ");
  const workspacePublished = Boolean(
    workspace && (setup.target === "full-course"
      ? fullCourseLectureIds.length > 0 && fullCoursePublishedCount === fullCourseLectureIds.length
      : publishedLectureIds.includes(workspace.lectureId)),
  );
  const previewHref = canvas && workspace
    ? previewWorkspaceUrl(workspace.courseId, lectureFromWorkspace(workspace, setup, lectureSchedule))
    : null;
  const steps = builderSteps({ bundleReady, canvasReady: !!canvas, courseReady, mediaReady, workspacePublished });
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
      bundleReady,
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
    setGeneratedLectureIds([]);
    setVideos([]);
    setSelectedVideos(new Set());
    setMediaIncluded(false);
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
              onWorkspaceLecturesChange(created.course, created.lectures);
              setGeneratedLectureIds([]);
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
              let skipped = 0;
              for (const file of uploadFiles) {
                try {
                  uploaded.push(await uploadCourseMaterial({
                    courseId: activeWorkspace.courseId,
                    path: uploadDestination(uploadPath, file, uploadFiles.length),
                    file,
                    session,
                  }));
                } catch (error) {
                  if (!isSkippableUploadError(error)) throw error;
                  skipped += 1;
                }
              }
              await updateBundleAndSchedule(activeWorkspace.courseId);
              if (setup.target !== "full-course") setActiveStep("review");
              if (uploaded.length === 1) return `Uploaded ${uploaded[0].path} as ${uploaded[0].kind}.`;
              const skippedText = skipped ? ` Skipped ${skipped} unsupported files.` : "";
              return `Uploaded ${uploaded.length} materials into the source bundle.${skippedText}`;
            })}
            onScan={() => run("scan", async () => {
              const activeWorkspace = requireWorkspace(workspace);
              await updateBundleAndSchedule(activeWorkspace.courseId);
              if (setup.target !== "full-course") setActiveStep("review");
              return "Uploaded source bundle scanned.";
            })}
            onApplySchedule={() => run("apply-schedule", async () => {
              const created = await createCourseWorkspace(setup, session, lectureSchedule);
              setWorkspace({ courseId: created.course.id, lectureId: created.active_lecture_id });
              onWorkspaceLecturesChange(created.course, created.lectures);
              setGeneratedLectureIds([]);
              setCanvas(null);
              setActiveStep("review");
              return `Lecture schedule applied with ${created.lectures.length} dated lectures.`;
            })}
          />
        ) : null}
        {activeStep === "generate" ? (
          <ProfessorCanvasDraftStep
            canvas={canvas}
            canGenerate={Boolean(bundleReady && workspace)}
            generatedCount={generatedLectureIds.length}
            isFullCourse={setup.target === "full-course"}
            isGenerating={pendingAction === "generate"}
            previewHref={previewHref}
            totalCount={fullCourseLectureIds.length}
            onGenerate={() => run("generate", async () => {
              const activeWorkspace = requireWorkspace(workspace);
              const lectureIds = setup.target === "full-course" && fullCourseLectureIds.length
                ? fullCourseLectureIds
                : [activeWorkspace.lectureId];
              const canvases = await generateLectureCanvasDrafts({
                lectureIds,
                draft: (lectureId) => draftLectureCanvas(activeWorkspace.courseId, lectureId, session),
              });
              const firstCanvas = canvases[0] ?? null;
              setCanvas(firstCanvas);
              setGeneratedLectureIds(lectureIds);
              setActiveStep("publish");
              if (lectureIds.length === 1) return "Course-builder agent generated a source-grounded canvas draft.";
              return `Course-builder agent generated ${lectureIds.length} source-grounded lecture canvases.`;
            })}
          />
        ) : null}
        {activeStep === "review" ? (
          <ProfessorReviewStep
            canContinue={Boolean(bundleReady && workspace)}
            canInclude={Boolean(selectedVideos.size && bundleReady && workspace)}
            canSearch={Boolean(setupReady && workspace)}
            pendingAction={pendingAction}
            onContinue={() => setActiveStep("generate")}
            onInclude={() => run("include-videos", async () => {
              const activeWorkspace = requireWorkspace(workspace);
              const selected = videos.filter((video) => selectedVideos.has(video.video_id));
              for (const video of selected) {
                await includeYoutubeMedia({
                  courseId: activeWorkspace.courseId,
                  video,
                  session,
                });
              }
              setSelectedVideos(new Set());
              setMediaIncluded(true);
              if (canvas) setCanvas(null);
              setGeneratedLectureIds([]);
              setActiveStep("generate");
              return `Saved ${selected.length} approved video${selected.length === 1 ? "" : "s"} for draft generation.`;
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
            ready={mediaReady}
            selectedVideos={selectedVideos}
            videos={videos}
          />
        ) : null}
        {activeStep === "publish" ? (
          <ProfessorPublishStep
            canPublish={Boolean(canvas && workspace)}
            isFullCourse={setup.target === "full-course"}
            isPublishing={pendingAction === "publish"}
            onPublish={() => run("publish", async () => {
              const activeWorkspace = requireWorkspace(workspace);
              const lectureIds = setup.target === "full-course"
                ? (generatedLectureIds.length ? generatedLectureIds : fullCourseLectureIds)
                : [activeWorkspace.lectureId];
              const published = [];
              for (const lectureId of lectureIds) {
                try {
                  published.push(await onPublishWorkspace(activeWorkspace.courseId, lectureId));
                } catch (error) {
                  if (setup.target !== "full-course") throw error;
                  await draftLectureCanvas(activeWorkspace.courseId, lectureId, session);
                  published.push(await onPublishWorkspace(activeWorkspace.courseId, lectureId));
                }
              }
              const lastPublished = published[published.length - 1];
              const when = lastPublished?.published_at ? ` at ${new Date(lastPublished.published_at).toLocaleString()}` : "";
              if (published.length === 1) return `Tutor workspace published as version ${lastPublished.version ?? 1}${when}.`;
              return `${published.length} tutor workspaces published for students${when}.`;
            })}
            publishedCount={fullCoursePublishedCount}
            ready={workspacePublished}
            totalCount={fullCourseLectureIds.length}
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

function lectureIdFromNumber(number: string) {
  const parsed = Number(number);
  return Number.isFinite(parsed) ? `lecture-${parsed.toString().padStart(2, "0")}` : `lecture-${number}`;
}

function isSkippableUploadError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  return /File type .* is not writable|Hidden workspace paths are not allowed|files are limited to/i.test(message);
}
