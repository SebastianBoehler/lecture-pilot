import { useEffect, useState } from "react";
import { draftLectureCanvas, getCourseLectures, getDraftLectureCanvas } from "./api";
import { builderSteps, initialBuilderStep, ProfessorBuilderStepper, type BuilderStep } from "./ProfessorBuilderStepper";
import { ProfessorCanvasDraftStep } from "./ProfessorCanvasDraftStep";
import { ProfessorGenerationWarnings } from "./ProfessorGenerationWarnings";
import { generateLectureCanvasDrafts, type CanvasGenerationProgress } from "./professorCanvasGeneration";
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
import { publishLectureRows } from "./professorPublishRows";
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
  const [generationProgress, setGenerationProgress] = useState<CanvasGenerationProgress[]>([]);
  const [generationWarnings, setGenerationWarnings] = useState<string[]>([]);
  const [query, setQuery] = useState(savedFlow.query);
  const [videos, setVideos] = useState<YoutubeVideoCandidate[]>([]);
  const [selectedVideos, setSelectedVideos] = useState<Set<string>>(new Set());
  const [mediaIncluded, setMediaIncluded] = useState(false);
  const [mediaReviewed, setMediaReviewed] = useState(false);
  const [scheduleApplied, setScheduleApplied] = useState(setup.target !== "full-course");
  const { error, notice, pendingAction, run, setError } = useProfessorWorkflowRun();
  const [restored, setRestored] = useState(!savedFlow.bundleReady && !savedFlow.canvasReady);
  const [isRestoring, setIsRestoring] = useState(false);
  const setupReady = isCourseSetupReady(setup);
  const bundleReady = Boolean(bundle?.files.length);
  const mediaReady = mediaIncluded || selectedVideos.size > 0 || hasCanvasVideo(canvas);
  const reviewReady = mediaReady || mediaReviewed;
  const reviewAvailable = bundleReady && (setup.target !== "full-course" || scheduleApplied);
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
  const publishLectures = workspace ? publishLectureRows({
    courseId: workspace.courseId,
    lectureSchedule,
    previewWorkspaceUrl,
    publishedLectureIds,
    setup,
    workspaceLecture: lectureFromWorkspace(workspace, setup, lectureSchedule),
  }) : [];
  const steps = builderSteps({
    bundleReady,
    canvasReady: !!canvas,
    courseReady,
    reviewAvailable,
    reviewReady,
    workspacePublished,
  });
  useEffect(() => {
    let cancelled = false;
    async function restoreGeneratedState() {
      await restoreFromBackend(savedFlow.workspace, { quietDraftMiss: !savedFlow.canvasReady, skipWhenMissing: true });
      if (!cancelled) setRestored(true);
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
    setGenerationProgress([]);
    setGenerationWarnings([]);
    setVideos([]);
    setSelectedVideos(new Set());
    setMediaIncluded(false);
    setMediaReviewed(false);
    setScheduleApplied(nextSetup.target !== "full-course");
    setActiveStep("define");
  }
  return (
    <main className="professor-screen">
      <section className="professor-page-header">
        <div>
          <h1>Course builder</h1>
          <p>Define the course scope, upload material, draft the canvas, approve media, then publish for students.</p>
        </div>
        <div className="professor-header-actions">
          <button
            className="refresh-button"
            disabled={!workspace || isRestoring}
            type="button"
            onClick={() => {
              void restoreFromBackend(workspace, { quietDraftMiss: true });
            }}
          >
            {isRestoring ? "Refreshing..." : "Refresh workspace state"}
          </button>
          <p className="professor-session">Signed in as {session.username}</p>
        </div>
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
              setGenerationProgress([]);
              setGenerationWarnings([]);
              setScheduleApplied(setup.target !== "full-course");
              setCourseReady(true);
              setActiveStep("upload");
              return setup.target === "full-course"
                ? `Course workspace ${created.course.id} ready. Upload materials to infer the lecture schedule.`
                : `Course workspace ${created.course.id}/${created.active_lecture_id} ready.`;
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
              setCanvas(null);
              setGeneratedLectureIds([]);
              setGenerationProgress([]);
              setGenerationWarnings([]);
              setMediaIncluded(false);
              setMediaReviewed(false);
              setSelectedVideos(new Set());
              if (setup.target === "full-course") setScheduleApplied(false);
              if (setup.target !== "full-course") setActiveStep("review");
              if (uploaded.length === 1) return `Uploaded ${uploaded[0].path} as ${uploaded[0].kind}.`;
              const skippedText = skipped ? ` Skipped ${skipped} unsupported files.` : "";
              return `Uploaded ${uploaded.length} materials into the source bundle.${skippedText}`;
            })}
            onScan={() => run("scan", async () => {
              const activeWorkspace = requireWorkspace(workspace);
              await updateBundleAndSchedule(activeWorkspace.courseId);
              setCanvas(null);
              setGeneratedLectureIds([]);
              setGenerationProgress([]);
              setGenerationWarnings([]);
              setMediaIncluded(false);
              setMediaReviewed(false);
              setSelectedVideos(new Set());
              if (setup.target === "full-course") setScheduleApplied(false);
              if (setup.target !== "full-course") setActiveStep("review");
              return "Uploaded source bundle scanned.";
            })}
            onApplySchedule={() => run("apply-schedule", async () => {
              const created = await createCourseWorkspace(setup, session, lectureSchedule);
              setWorkspace({ courseId: created.course.id, lectureId: created.active_lecture_id });
              onWorkspaceLecturesChange(created.course, created.lectures);
              setGeneratedLectureIds([]);
              setCanvas(null);
              setGenerationProgress([]);
              setGenerationWarnings([]);
              setMediaReviewed(false);
              setScheduleApplied(true);
              setActiveStep("review");
              return `Lecture schedule applied with ${created.lectures.length} dated lectures.`;
            })}
          />
        ) : null}
        {activeStep === "generate" ? (
          <ProfessorCanvasDraftStep
            canvas={canvas}
            canGenerate={Boolean(bundleReady && reviewReady && workspace)}
            generationProgress={generationProgress}
            generatedCount={generatedLectureIds.length}
            isFullCourse={setup.target === "full-course"}
            isGenerating={pendingAction === "generate"}
            previewHref={previewHref}
            totalCount={fullCourseLectureIds.length}
            warnings={generationWarnings}
            onGenerate={() => run("generate", async () => {
              const activeWorkspace = requireWorkspace(workspace);
              const lectureIds = setup.target === "full-course" && fullCourseLectureIds.length
                ? fullCourseLectureIds
                : [activeWorkspace.lectureId];
              setGenerationProgress(lectureIds.map((lectureId) => ({ lectureId, status: "pending" })));
              setGenerationWarnings([]);
              const canvases = await generateLectureCanvasDrafts({
                lectureIds,
                draft: (lectureId) => draftLectureCanvas(activeWorkspace.courseId, lectureId, session),
                onProgress: (progress) => {
                  setGenerationProgress((current) => current.map((item) => (
                    item.lectureId === progress.lectureId ? { ...item, ...progress } : item
                  )));
                },
              });
              const firstCanvas = canvases[0] ?? null;
              setCanvas(firstCanvas);
              setGeneratedLectureIds(lectureIds);
              setGenerationWarnings(Array.from(new Set(canvases.flatMap((item) => item.warnings ?? []))));
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
            onContinue={() => {
              setMediaReviewed(true);
              setActiveStep("generate");
            }}
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
              setMediaReviewed(true);
              if (canvas) setCanvas(null);
              setGeneratedLectureIds([]);
              setGenerationProgress([]);
              setGenerationWarnings([]);
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
            lectures={publishLectures}
            ready={workspacePublished}
            totalCount={fullCourseLectureIds.length}
          />
        ) : null}
      </div>
      <ProfessorGenerationWarnings warnings={generationWarnings} />
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

  async function restoreFromBackend(
    targetWorkspace: { courseId: string; lectureId: string } | null,
    options: { quietDraftMiss?: boolean; skipWhenMissing?: boolean } = {},
  ) {
    if (!targetWorkspace) {
      if (!options.skipWhenMissing) setError("Create a course workspace before refreshing state.");
      return;
    }
    setIsRestoring(true);
    try {
      const restoredBundle = await getSourceBundle(targetWorkspace.courseId, session);
      setBundle(restoredBundle);
      if (setup.target === "full-course" && !lectureSchedule.length) {
        const restoredLectures = await getCourseLectures(targetWorkspace.courseId, session);
        setLectureSchedule(restoredLectures.map(scheduleItemFromLecture));
      }
      try {
        const restoredCanvas = await getDraftLectureCanvas(targetWorkspace.courseId, targetWorkspace.lectureId, session);
        setCanvas(restoredCanvas);
        setGenerationWarnings(restoredCanvas.warnings ?? []);
        setActiveStep("publish");
      } catch (canvasError) {
        if (!options.quietDraftMiss) {
          setError(canvasError instanceof Error ? canvasError.message : "Could not restore professor preview.");
        }
      }
    } catch (restoreError) {
      if (!options.skipWhenMissing) {
        setError(restoreError instanceof Error ? restoreError.message : "Could not refresh workspace state.");
      }
    } finally {
      setIsRestoring(false);
    }
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

function scheduleItemFromLecture(lecture: ReturnType<typeof lectureFromWorkspace>): LectureScheduleItem {
  return {
    date: lecture.date,
    material_path: lecture.materialPath,
    number: lecture.number,
    title: lecture.title,
  };
}
