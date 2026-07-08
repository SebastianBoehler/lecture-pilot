import { useEffect, useState } from "react";

import { draftLectureCanvas, getCourseLectures, getDraftLectureCanvas } from "./api";
import { builderSteps, initialBuilderStep, type BuilderStep } from "./ProfessorBuilderStepper";
import { generateLectureCanvasDrafts, type CanvasGenerationProgress } from "./professorCanvasGeneration";
import { hasCanvasVideo, toggleSelected } from "./ProfessorCourseBuilderParts";
import {
  createCourseWorkspace,
  getSourceBundle,
  includeYoutubeMedia,
  proposeLectureSchedule,
  searchYoutubeMedia,
  uploadCourseMaterial,
} from "./professorApi";
import { isCourseSetupReady, readSavedFlow, writeSavedFlow, type CourseSetup } from "./professorBuilderState";
import {
  activationLectures,
  courseFromSetup,
  lectureIdFromNumber,
  scheduleItemFromLecture,
} from "./professorWorkspaceActivation";
import { publishLectureRows } from "./professorPublishRows";
import { useProfessorWorkflowRun } from "./professorWorkflowRun";
import { lectureFromWorkspace, requireWorkspace } from "./professorWorkspaceView";
import { uploadDestination } from "./professorUpload";
import {
  flattenVideoGroups,
  type YoutubeCandidateGroup,
  youtubeSuggestionQueries,
} from "./professorYoutubeSuggestions";
import type {
  CanvasDocument,
  CanvasPublicationResult,
  LectureScheduleItem,
  LoginSession,
  SourceBundleManifest,
  UniversityCourse,
  YoutubeVideoCandidate,
} from "./types";

export type ProfessorCourseBuilderProps = {
  session: LoginSession;
  onPublishWorkspace: (courseId: string, lectureId: string) => Promise<CanvasPublicationResult>;
  onWorkspacePublished: (course: UniversityCourse, lectures: ReturnType<typeof lectureFromWorkspace>[]) => void;
  previewWorkspaceUrl: (courseId: string, lecture: ReturnType<typeof lectureFromWorkspace>) => string;
  publishedLectureIds: string[];
};

export function useProfessorCourseBuilder({
  session,
  onPublishWorkspace,
  onWorkspacePublished,
  previewWorkspaceUrl,
  publishedLectureIds,
}: ProfessorCourseBuilderProps) {
  const [savedFlow] = useState(readSavedFlow);
  const [setup, setSetup] = useState(savedFlow.setup);
  const [workspace, setWorkspace] = useState(savedFlow.workspace);
  const [workspaceCourse, setWorkspaceCourse] = useState<UniversityCourse | null>(null);
  const [workspaceLectures, setWorkspaceLectures] = useState<ReturnType<typeof lectureFromWorkspace>[]>([]);
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
  const [suggestedVideoGroups, setSuggestedVideoGroups] = useState<YoutubeCandidateGroup[]>([]);
  const [selectedVideos, setSelectedVideos] = useState<Set<string>>(new Set());
  const [autoSuggestedSearchKey, setAutoSuggestedSearchKey] = useState<string | null>(null);
  const [autoSuggesting, setAutoSuggesting] = useState(false);
  const [mediaLectureId, setMediaLectureId] = useState(savedFlow.workspace?.lectureId ?? "");
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
  const mediaTargetLectures = workspace
    ? setup.target === "full-course"
      ? workspaceLectures.length ? workspaceLectures : activationLectures(workspace, setup, lectureSchedule)
      : [lectureFromWorkspace(workspace, setup, lectureSchedule)]
    : [];
  const mediaTargetLectureKey = mediaTargetLectures.map((lecture) => lecture.id).join("|");
  const fullCourseLectureIds = setup.target === "full-course" && scheduledLectureIds.length
    ? scheduledLectureIds
    : workspace ? [workspace.lectureId] : [];
  const fullCoursePublishedCount = fullCourseLectureIds.filter((lectureId) => publishedLectureIds.includes(lectureId)).length;
  const materialScope = setup.target === "full-course" ? "all course materials" : "materials for this lecture";
  const defaultYoutubeQuery = [
    setup.courseTitle,
    setup.target === "single-lecture" ? setup.lectureTitle : "machine learning lecture",
  ].filter(Boolean).join(" ");
  const suggestedQueries = youtubeSuggestionQueries(setup, lectureSchedule);
  const suggestedSearchKey = workspace && suggestedQueries.length
    ? [
      workspace.courseId,
      bundle?.files.map((file) => `${file.path}:${file.size_bytes}`).join(",") ?? "no-bundle",
      suggestedQueries.join("|"),
    ].join("::")
    : "";
  const availableVideos = flattenVideoGroups([
    ...suggestedVideoGroups,
    { query: query.trim() || defaultYoutubeQuery, videos },
  ]);
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
    if (!mediaTargetLectureKey) {
      if (mediaLectureId) setMediaLectureId("");
      return;
    }
    const ids = mediaTargetLectureKey.split("|");
    if (!ids.includes(mediaLectureId)) setMediaLectureId(ids[0]);
  }, [mediaLectureId, mediaTargetLectureKey]);

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

  useEffect(() => {
    if (
      activeStep !== "review"
      || !workspace
      || !setupReady
      || !suggestedQueries.length
      || !suggestedSearchKey
      || pendingAction !== null
      || autoSuggestedSearchKey === suggestedSearchKey
    ) return;
    let cancelled = false;
    setAutoSuggestedSearchKey(suggestedSearchKey);
    setAutoSuggesting(true);
    setError(null);
    void searchSuggestedVideos(workspace.courseId)
      .catch((autoError) => {
        if (!cancelled) setError(autoError instanceof Error ? autoError.message : "YouTube suggestions failed.");
      })
      .finally(() => {
        if (!cancelled) setAutoSuggesting(false);
      });
    return () => {
      cancelled = true;
    };
  }, [
    activeStep,
    autoSuggestedSearchKey,
    pendingAction,
    setError,
    setupReady,
    suggestedQueries.length,
    suggestedSearchKey,
    workspace,
  ]);

  function updateSetup(nextSetup: CourseSetup) {
    setSetup(nextSetup);
    resetGeneratedState();
    setWorkspace(null);
    setWorkspaceCourse(null);
    setWorkspaceLectures([]);
    setCourseReady(false);
    setBundle(null);
    setLectureSchedule([]);
    setMediaLectureId("");
    setScheduleApplied(nextSetup.target !== "full-course");
    setActiveStep("define");
  }

  function resetGeneratedState() {
    setCanvas(null);
    setGeneratedLectureIds([]);
    setGenerationProgress([]);
    setGenerationWarnings([]);
    setVideos([]);
    setSuggestedVideoGroups([]);
    setAutoSuggestedSearchKey(null);
    setAutoSuggesting(false);
    setSelectedVideos(new Set());
    setMediaIncluded(false);
    setMediaReviewed(false);
  }

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

  async function searchSuggestedVideos(courseId: string) {
    const groups: YoutubeCandidateGroup[] = [];
    const seenVideoIds = new Set<string>();
    for (const searchQuery of suggestedQueries) {
      const response = await searchYoutubeMedia(courseId, searchQuery, session, 3);
      const groupVideos = response.items.filter((video) => {
        if (seenVideoIds.has(video.video_id)) return false;
        seenVideoIds.add(video.video_id);
        return true;
      });
      groups.push({ query: searchQuery, videos: groupVideos });
    }
    setSuggestedVideoGroups(groups);
    return flattenVideoGroups(groups).length;
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
      const restoredLectures = await getCourseLectures(targetWorkspace.courseId, session);
      setWorkspaceLectures(restoredLectures);
      setWorkspaceCourse((current) => current ?? courseFromSetup(targetWorkspace.courseId, setup, session));
      if (setup.target === "full-course" && !lectureSchedule.length) {
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

  const defineStep = {
    courseReady,
    isCreating: pendingAction === "create",
    isReady: setupReady,
    onCreate: () => run("create", async () => {
      const schedule = setup.target === "full-course" ? lectureSchedule : [];
      const created = await createCourseWorkspace(setup, session, schedule);
      setWorkspace({ courseId: created.course.id, lectureId: created.active_lecture_id });
      setMediaLectureId(created.active_lecture_id);
      setWorkspaceCourse(created.course);
      setWorkspaceLectures(created.lectures);
      resetGeneratedState();
      setScheduleApplied(setup.target !== "full-course");
      setCourseReady(true);
      setActiveStep("upload");
      return setup.target === "full-course"
        ? `Course workspace ${created.course.id} ready. Upload materials to infer the lecture schedule.`
        : `Course workspace ${created.course.id}/${created.active_lecture_id} ready.`;
    }),
    onSetupChange: updateSetup,
    setup,
  };

  const uploadStep = {
    bundle,
    courseReady,
    lectureSchedule,
    materialScope,
    pendingAction,
    setup,
    uploadFiles,
    uploadPath,
    workspaceReady: Boolean(workspace),
    setUploadPath,
    onUploadFilesChange: setUploadFiles,
    onScheduleChange: setLectureSchedule,
    onUpload: () => run("upload", async () => {
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
      resetGeneratedState();
      if (setup.target === "full-course") setScheduleApplied(false);
      if (setup.target !== "full-course") setActiveStep("review");
      if (uploaded.length === 1) return `Uploaded ${uploaded[0].path} as ${uploaded[0].kind}.`;
      const skippedText = skipped ? ` Skipped ${skipped} unsupported files.` : "";
      return `Uploaded ${uploaded.length} materials into the source bundle.${skippedText}`;
    }),
    onScan: () => run("scan", async () => {
      const activeWorkspace = requireWorkspace(workspace);
      await updateBundleAndSchedule(activeWorkspace.courseId);
      resetGeneratedState();
      if (setup.target === "full-course") setScheduleApplied(false);
      if (setup.target !== "full-course") setActiveStep("review");
      return "Uploaded source bundle scanned.";
    }),
    onApplySchedule: () => run("apply-schedule", async () => {
      const created = await createCourseWorkspace(setup, session, lectureSchedule);
      setWorkspace({ courseId: created.course.id, lectureId: created.active_lecture_id });
      setMediaLectureId(created.active_lecture_id);
      setWorkspaceCourse(created.course);
      setWorkspaceLectures(created.lectures);
      resetGeneratedState();
      setScheduleApplied(true);
      setActiveStep("review");
      return `Lecture schedule applied with ${created.lectures.length} dated lectures.`;
    }),
  };

  const generateStep = {
    canvas,
    canGenerate: Boolean(bundleReady && reviewReady && workspace),
    generationProgress,
    generatedCount: generatedLectureIds.length,
    isFullCourse: setup.target === "full-course",
    isGenerating: pendingAction === "generate",
    previewHref,
    totalCount: fullCourseLectureIds.length,
    warnings: generationWarnings,
    onGenerate: () => run("generate", async () => {
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
      setCanvas(canvases[0] ?? null);
      setGeneratedLectureIds(lectureIds);
      setGenerationWarnings(Array.from(new Set(canvases.flatMap((item) => item.warnings ?? []))));
      setActiveStep("publish");
      if (lectureIds.length === 1) return "Course-builder agent generated a source-grounded canvas draft.";
      return `Course-builder agent generated ${lectureIds.length} source-grounded lecture canvases.`;
    }),
  };

  const mediaStep = {
    canContinue: Boolean(bundleReady && workspace),
    canInclude: Boolean(selectedVideos.size && bundleReady && workspace && mediaLectureId),
    canSearch: Boolean(setupReady && workspace),
    canSuggest: Boolean(suggestedQueries.length && setupReady && workspace),
    pendingAction: autoSuggesting ? "suggest-videos" : pendingAction,
    onContinue: () => {
      setMediaReviewed(true);
      setActiveStep("generate");
    },
    onInclude: () => run("include-videos", async () => {
      const activeWorkspace = requireWorkspace(workspace);
      const selected = availableVideos.filter((video) => selectedVideos.has(video.video_id));
      for (const video of selected) {
        await includeYoutubeMedia({
          courseId: activeWorkspace.courseId,
          lectureId: mediaLectureId || activeWorkspace.lectureId,
          video,
          session,
        });
      }
      const target = mediaTargetLectures.find((lecture) => lecture.id === (mediaLectureId || activeWorkspace.lectureId));
      setSelectedVideos(new Set());
      setMediaIncluded(true);
      setMediaReviewed(true);
      if (canvas) setCanvas(null);
      setGeneratedLectureIds([]);
      setGenerationProgress([]);
      setGenerationWarnings([]);
      setActiveStep("generate");
      const targetLabel = target ? ` for lecture ${target.number}` : "";
      return `Saved ${selected.length} approved video${selected.length === 1 ? "" : "s"}${targetLabel}.`;
    }),
    onQueryChange: setQuery,
    onSearch: () => run("search", async () => {
      const searchQuery = query.trim() || defaultYoutubeQuery;
      if (!query.trim()) setQuery(searchQuery);
      const activeWorkspace = requireWorkspace(workspace);
      const response = await searchYoutubeMedia(activeWorkspace.courseId, searchQuery, session);
      setVideos(response.items);
      return `Found ${response.items.length} YouTube candidates.`;
    }),
    onSuggest: () => run("suggest-videos", async () => {
      const activeWorkspace = requireWorkspace(workspace);
      const count = await searchSuggestedVideos(activeWorkspace.courseId);
      setAutoSuggestedSearchKey(suggestedSearchKey || null);
      return `Found ${count} suggested YouTube candidates from ${suggestedQueries.length} searches.`;
    }),
    onTargetLectureChange: setMediaLectureId,
    onToggleVideo: (videoId: string) => setSelectedVideos(toggleSelected(selectedVideos, videoId)),
    query,
    ready: mediaReady,
    selectedVideos,
    suggestedGroups: suggestedVideoGroups,
    suggestedQueries,
    targetLectureId: mediaLectureId,
    targetLectures: mediaTargetLectures,
    videos,
  };

  const publishStep = {
    canPublish: Boolean(canvas && workspace),
    isFullCourse: setup.target === "full-course",
    isPublishing: pendingAction === "publish",
    onPublish: () => run("publish", async () => {
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
      onWorkspacePublished(
        workspaceCourse ?? courseFromSetup(activeWorkspace.courseId, setup, session),
        workspaceLectures.length ? workspaceLectures : activationLectures(activeWorkspace, setup, lectureSchedule),
      );
      const lastPublished = published[published.length - 1];
      const when = lastPublished?.published_at ? ` at ${new Date(lastPublished.published_at).toLocaleString()}` : "";
      if (published.length === 1) return `Tutor workspace published as version ${lastPublished.version ?? 1}${when}.`;
      return `${published.length} tutor workspaces published for students${when}.`;
    }),
    publishedCount: fullCoursePublishedCount,
    lectures: publishLectures,
    ready: workspacePublished,
    totalCount: fullCourseLectureIds.length,
  };

  return {
    activeStep,
    defineStep,
    error,
    generateStep,
    generationWarnings,
    isRestoring,
    mediaStep,
    notice,
    publishStep,
    restoreWorkspace: () => void restoreFromBackend(workspace, { quietDraftMiss: true }),
    setActiveStep,
    steps,
    uploadStep,
    workspace,
  };
}

function isSkippableUploadError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  return /File type .* is not writable|Hidden workspace paths are not allowed|files are limited to/i.test(message);
}
