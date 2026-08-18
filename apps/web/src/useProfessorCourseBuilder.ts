import { useEffect, useEffectEvent, useRef, useState } from "react";

import { getCourseLectures, getDraftLectureCanvas } from "./api";
import { draftLectureCanvas, repairLectureCanvas } from "./canvasDraftApi";
import { builderSteps, initialBuilderStep, type BuilderStep } from "./ProfessorBuilderStepper";
import {
  CanvasGenerationBatchError,
  generateLectureCanvasDrafts,
  type CanvasGenerationProgress,
} from "./professorCanvasGeneration";
import { restoreFullCourseCanvasDrafts } from "./professorCanvasRestoration";
import { hasCanvasVideo, toggleSelected } from "./ProfessorCourseBuilderParts";
import {
  createCourseWorkspace,
  getSourceBundle,
  includeYoutubeMedia,
  listCourseWorkspaces,
  listYoutubeMedia,
  proposeLectureSchedule,
  removeYoutubeMedia,
  searchYoutubeMedia,
} from "./professorApi";
import {
  clearSavedFlow,
  isCourseSetupReady,
  readSavedFlow,
  writeSavedFlow,
  type CourseSetup,
} from "./professorBuilderState";
import {
  activationLectures,
  courseFromSetup,
  lectureIdFromNumber,
  scheduleItemFromLecture,
} from "./professorWorkspaceActivation";
import { publishLectureRows } from "./professorPublishRows";
import { useCourseTitleSuggestions } from "./useCourseTitleSuggestions";
import { useProfessorWorkflowRun } from "./professorWorkflowRun";
import { useProfessorSourceRouting } from "./useProfessorSourceRouting";
import { lectureFromWorkspace, requireWorkspace } from "./professorWorkspaceView";
import { uploadProfessorMaterials } from "./professorMaterialUpload";
import { ignoredUploadNotice } from "./professorUpload";
import { hasNoAssignedEvidence } from "./sourceRoutingView";
import {
  flattenVideoGroups,
  type YoutubeCandidateGroup,
  youtubeSuggestionQueries,
} from "./professorYoutubeSuggestions";
import type {
  CanvasDocument,
  CanvasPublicationResult,
  CourseMaterialUploadType,
  LectureScheduleItem,
  LoginSession,
  SourceBundleManifest,
  UniversityCourse,
  YoutubeVideoCandidate,
} from "./types";

export type ProfessorCourseBuilderProps = {
  session: LoginSession;
  onPublishWorkspace: (courseId: string, lectureId: string) => Promise<CanvasPublicationResult>;
  onWorkspacePublished: (
    course: UniversityCourse,
    lectures: ReturnType<typeof lectureFromWorkspace>[],
  ) => void;
  previewWorkspaceUrl: (
    courseId: string,
    lecture: ReturnType<typeof lectureFromWorkspace>,
  ) => string;
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
  const [workspaceLectures, setWorkspaceLectures] = useState<
    ReturnType<typeof lectureFromWorkspace>[]
  >([]);
  const [courseReady, setCourseReady] = useState(
    savedFlow.courseReady && Boolean(savedFlow.workspace),
  );
  const [activeStep, setActiveStep] = useState<BuilderStep>(() =>
    initialBuilderStep({
      bundleReady: savedFlow.bundleReady,
      canvasReady: savedFlow.canvasReady,
      courseReady: savedFlow.courseReady && Boolean(savedFlow.workspace),
    }),
  );
  const [bundle, setBundle] = useState<SourceBundleManifest | null>(null);
  const [supportedUploads, setSupportedUploads] = useState<CourseMaterialUploadType[]>([]);
  const [lectureSchedule, setLectureSchedule] = useState<LectureScheduleItem[]>(
    savedFlow.lectureSchedule,
  );
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [canvas, setCanvas] = useState<CanvasDocument | null>(null);
  const [generatedLectureIds, setGeneratedLectureIds] = useState<string[]>([]);
  const [draftReviewed, setDraftReviewed] = useState(false);
  const [generationProgress, setGenerationProgress] = useState<CanvasGenerationProgress[]>([]);
  const [generationWarnings, setGenerationWarnings] = useState<string[]>([]);
  const [retryingLectureIds, setRetryingLectureIds] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState(savedFlow.query);
  const [videos, setVideos] = useState<YoutubeVideoCandidate[]>([]);
  const [suggestedVideoGroups, setSuggestedVideoGroups] = useState<YoutubeCandidateGroup[]>([]);
  const [selectedVideos, setSelectedVideos] = useState<Set<string>>(new Set());
  const [autoSuggestedSearchKey, setAutoSuggestedSearchKey] = useState<string | null>(null);
  const suggestedSearchGeneration = useRef(0);
  const mediaSelectionGeneration = useRef(0);
  const [, setAutoSuggesting] = useState(false);
  const [mediaLectureId, setMediaLectureId] = useState(savedFlow.workspace?.lectureId ?? "");
  const [mediaIncluded, setMediaIncluded] = useState(false);
  const [mediaReviewed, setMediaReviewed] = useState(false);
  const [scheduleApplied, setScheduleApplied] = useState(setup.target !== "full-course");
  const sourceRouting = useProfessorSourceRouting(session);
  const { error, notice, pendingAction, run, setError } = useProfessorWorkflowRun();
  const [restored, setRestored] = useState(!savedFlow.bundleReady && !savedFlow.canvasReady);
  const [isRestoring, setIsRestoring] = useState(false);
  const restoreGeneratedState = useEffectEvent(restoreFromBackend);
  const runAutomaticVideoSearch = useEffectEvent(searchSuggestedVideos);

  const setupReady = isCourseSetupReady(setup);
  const { courseSearchFailed, courseSuggestions } = useCourseTitleSuggestions({
    enabled: activeStep === "define" && !courseReady,
    personalCourses: session.university_courses ?? [],
    query: setup.courseTitle,
    session,
  });
  const bundleReady = Boolean(bundle?.files.length);
  const mediaReady = mediaIncluded || selectedVideos.size > 0 || hasCanvasVideo(canvas);
  const reviewReady = mediaReady || mediaReviewed;
  const reviewAvailable = bundleReady && (setup.target !== "full-course" || scheduleApplied);
  const routingReady = Boolean(
    sourceRouting.routing?.confirmed && !hasNoAssignedEvidence(sourceRouting.routing.routes),
  );
  const scheduledLectureIds = lectureSchedule.map((lecture) => lectureIdFromNumber(lecture.number));
  const mediaTargetLectures = workspace
    ? setup.target === "full-course"
      ? workspaceLectures.length
        ? workspaceLectures
        : activationLectures(workspace, setup, lectureSchedule)
      : [lectureFromWorkspace(workspace, setup, lectureSchedule)]
    : [];
  const mediaTargetLectureKey = mediaTargetLectures.map((lecture) => lecture.id).join("|");
  const mediaTargetLecture =
    mediaTargetLectures.find((lecture) => lecture.id === mediaLectureId) ?? mediaTargetLectures[0];
  const fullCourseLectureIds =
    setup.target === "full-course" && scheduledLectureIds.length
      ? scheduledLectureIds
      : workspace
        ? [workspace.lectureId]
        : [];
  const fullCoursePublishedCount = fullCourseLectureIds.filter((lectureId) =>
    publishedLectureIds.includes(lectureId),
  ).length;
  const suggestedQueries = youtubeSuggestionQueries(setup, mediaTargetLecture);
  const defaultYoutubeQuery = suggestedQueries[0] ?? setup.courseTitle.trim();
  const mediaCourseId = workspace?.courseId ?? "";
  const mediaTargetLectureId = mediaTargetLecture?.id ?? "";
  const mediaSearchScopeKey =
    mediaCourseId && mediaTargetLectureId ? `${mediaCourseId}:${mediaTargetLectureId}` : "";
  const suggestedSearchKey =
    workspace && suggestedQueries.length
      ? [
          workspace.courseId,
          mediaTargetLecture?.id ?? "no-lecture",
          bundle?.files.map((file) => `${file.path}:${file.size_bytes}`).join(",") ?? "no-bundle",
          suggestedQueries.join("|"),
        ].join("::")
      : "";
  const availableVideos = flattenVideoGroups([
    ...suggestedVideoGroups,
    { query: query.trim() || defaultYoutubeQuery, videos },
  ]);
  const workspacePublished = Boolean(
    workspace &&
    (setup.target === "full-course"
      ? fullCourseLectureIds.length > 0 && fullCoursePublishedCount === fullCourseLectureIds.length
      : publishedLectureIds.includes(workspace.lectureId)),
  );
  const previewHref =
    canvas && workspace
      ? previewWorkspaceUrl(
          workspace.courseId,
          lectureFromWorkspace(workspace, setup, lectureSchedule),
        )
      : null;
  const publishLectures = workspace
    ? publishLectureRows({
        courseId: workspace.courseId,
        lectureSchedule,
        previewWorkspaceUrl,
        publishedLectureIds,
        setup,
        workspaceLecture: lectureFromWorkspace(workspace, setup, lectureSchedule),
      })
    : [];
  const steps = builderSteps({
    bundleReady,
    canvasReady: !!canvas,
    courseReady,
    draftReviewed,
    reviewAvailable,
    reviewReady,
    routingReady,
    workspacePublished,
  });

  useEffect(() => {
    let cancelled = false;
    async function restoreSavedWorkspace() {
      await restoreGeneratedState(savedFlow.workspace, {
        quietDraftMiss: !savedFlow.canvasReady,
        skipWhenMissing: true,
      });
      if (!cancelled) setRestored(true);
    }
    if (!restored) void restoreSavedWorkspace();
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
    if (!mediaSearchScopeKey) return;
    suggestedSearchGeneration.current += 1;
    const selectionGeneration = ++mediaSelectionGeneration.current;
    setQuery(defaultYoutubeQuery);
    setVideos([]);
    setSuggestedVideoGroups([]);
    setSelectedVideos(new Set());
    setMediaIncluded(false);
    setAutoSuggestedSearchKey(null);
    if (!mediaCourseId || !mediaTargetLectureId) return;
    void listYoutubeMedia({
      courseId: mediaCourseId,
      lectureId: mediaTargetLectureId,
      session,
    })
      .then((selections) => {
        if (selectionGeneration !== mediaSelectionGeneration.current) return;
        setSelectedVideos(new Set(selections.map((selection) => selection.video.video_id)));
        setMediaIncluded(selections.length > 0);
      })
      .catch((selectionError) => {
        if (selectionGeneration === mediaSelectionGeneration.current) {
          setError(
            selectionError instanceof Error
              ? selectionError.message
              : "YouTube selections failed to load.",
          );
        }
      });
  }, [
    defaultYoutubeQuery,
    mediaCourseId,
    mediaSearchScopeKey,
    mediaTargetLectureId,
    session,
    setError,
  ]);

  useEffect(() => {
    if (!restored) return;
    writeSavedFlow({
      setup,
      workspace,
      courseReady,
      bundleReady,
      canvasReady: Boolean(canvas),
      lectureSchedule,
      query,
    });
  }, [bundleReady, canvas, courseReady, lectureSchedule, query, restored, setup, workspace]);

  useEffect(() => {
    if (
      activeStep !== "review" ||
      !workspace ||
      !setupReady ||
      !suggestedQueries.length ||
      !suggestedSearchKey ||
      pendingAction !== null ||
      autoSuggestedSearchKey === suggestedSearchKey
    )
      return;
    let cancelled = false;
    setAutoSuggestedSearchKey(suggestedSearchKey);
    setAutoSuggesting(true);
    setError(null);
    void runAutomaticVideoSearch(workspace.courseId)
      .catch((autoError) => {
        if (!cancelled)
          setError(autoError instanceof Error ? autoError.message : "YouTube suggestions failed.");
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
    setSupportedUploads([]);
    setLectureSchedule([]);
    setMediaLectureId("");
    setScheduleApplied(nextSetup.target !== "full-course");
    setActiveStep("define");
  }

  function resetGeneratedState() {
    sourceRouting.reset();
    setCanvas(null);
    setGeneratedLectureIds([]);
    setDraftReviewed(false);
    setGenerationProgress([]);
    setGenerationWarnings([]);
    setRetryingLectureIds(new Set());
    setVideos([]);
    setSuggestedVideoGroups([]);
    suggestedSearchGeneration.current += 1;
    mediaSelectionGeneration.current += 1;
    setAutoSuggestedSearchKey(null);
    setAutoSuggesting(false);
    setSelectedVideos(new Set());
    setMediaIncluded(false);
    setMediaReviewed(false);
  }

  async function searchSuggestedVideos(courseId: string) {
    const generation = ++suggestedSearchGeneration.current;
    const responses = await Promise.all(
      suggestedQueries.map(async (searchQuery) => {
        try {
          const response = await withTimeout(
            searchYoutubeMedia(courseId, searchQuery, session, 3),
            6000,
          );
          return { query: searchQuery, videos: response.items };
        } catch {
          return { query: searchQuery, videos: [] };
        }
      }),
    );
    const groups: YoutubeCandidateGroup[] = [];
    const seenVideoIds = new Set<string>();
    for (const response of responses) {
      const groupVideos = response.videos.filter((video) => {
        if (seenVideoIds.has(video.video_id)) return false;
        seenVideoIds.add(video.video_id);
        return true;
      });
      groups.push({ query: response.query, videos: groupVideos });
    }
    if (generation === suggestedSearchGeneration.current) setSuggestedVideoGroups(groups);
    return flattenVideoGroups(groups).length;
  }

  async function requireConfirmedRouting(courseId: string) {
    const current = await sourceRouting.load(courseId);
    if (current.confirmed && !hasNoAssignedEvidence(current.routes)) return;
    setActiveStep("sources");
    throw new Error(
      "Source assignments changed. Review and confirm source assignments again before generating canvases.",
    );
  }

  function updateGenerationItem(progress: CanvasGenerationProgress) {
    setGenerationProgress((current) =>
      current.map((item) =>
        item.lectureId === progress.lectureId
          ? { ...item, ...progress, errorKind: progress.errorKind, message: progress.message }
          : item,
      ),
    );
  }

  function recordGeneratedCanvas(lectureId: string, generatedCanvas: CanvasDocument) {
    setCanvas(generatedCanvas);
    setGeneratedLectureIds((current) =>
      current.includes(lectureId) ? current : [...current, lectureId],
    );
    setGenerationWarnings((current) =>
      Array.from(new Set([...current, ...(generatedCanvas.warnings ?? [])])),
    );
  }

  async function generateCanvases(
    courseId: string,
    lectureIds: string[],
    options: { repair?: boolean } = {},
  ) {
    try {
      return await generateLectureCanvasDrafts({
        lectureIds,
        draft: (lectureId) =>
          options.repair
            ? repairLectureCanvas(courseId, lectureId, session)
            : draftLectureCanvas(courseId, lectureId, session),
        onDraftReady: recordGeneratedCanvas,
        onProgress: updateGenerationItem,
      });
    } catch (generationError) {
      if (generationError instanceof CanvasGenerationBatchError) return null;
      throw generationError;
    }
  }

  async function retryCanvas(lectureId: string) {
    if (retryingLectureIds.has(lectureId)) return;
    setRetryingLectureIds((current) => new Set(current).add(lectureId));
    setError(null);
    try {
      const activeWorkspace = requireWorkspace(workspace);
      const repair =
        generationProgress.find((item) => item.lectureId === lectureId)?.errorKind === "repair";
      await generateCanvases(activeWorkspace.courseId, [lectureId], { repair });
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Canvas retry failed.");
    } finally {
      setRetryingLectureIds((current) => {
        const next = new Set(current);
        next.delete(lectureId);
        return next;
      });
    }
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
      if (options.skipWhenMissing) {
        const savedWorkspaceExists = (await listCourseWorkspaces(session)).some(
          (item) => item.course.id === targetWorkspace.courseId,
        );
        if (!savedWorkspaceExists) {
          clearSavedFlow();
          setQuery("");
          updateSetup({
            ...setup,
            courseTitle: "",
            firstLectureDate: "",
            lectureCount: "",
            lectureNumber: "",
            lectureTitle: "",
          });
          return;
        }
      }
      const restoredBundle = await getSourceBundle(targetWorkspace.courseId, session);
      setBundle(restoredBundle);
      setSupportedUploads(restoredBundle.supported_uploads ?? []);
      const restoredLectures = await getCourseLectures(targetWorkspace.courseId, session);
      setWorkspaceLectures(restoredLectures);
      setWorkspaceCourse(
        (current) => current ?? courseFromSetup(targetWorkspace.courseId, setup, session),
      );
      if (setup.target === "full-course" && !lectureSchedule.length) {
        setLectureSchedule(restoredLectures.map(scheduleItemFromLecture));
      }
      if (setup.target === "full-course") setScheduleApplied(restoredLectures.length > 0);
      let restoredRouting;
      try {
        restoredRouting = await sourceRouting.load(targetWorkspace.courseId);
      } catch (routingError) {
        setActiveStep("sources");
        setError(
          routingError instanceof Error
            ? routingError.message
            : "Source assignments failed to load.",
        );
        return;
      }
      if (setup.target === "full-course") {
        const restoredDrafts = await restoreFullCourseCanvasDrafts({
          courseId: targetWorkspace.courseId,
          lectureIds: restoredLectures.map((lecture) => lecture.id),
          session,
        });
        const activeCanvas =
          restoredDrafts.restored.find((item) => item.lectureId === targetWorkspace.lectureId)
            ?.canvas ?? restoredDrafts.restored[0]?.canvas;
        setCanvas(activeCanvas ?? null);
        setGeneratedLectureIds(restoredDrafts.restored.map((item) => item.lectureId));
        setGenerationProgress(restoredDrafts.progress);
        setGenerationWarnings(
          Array.from(
            new Set(restoredDrafts.restored.flatMap((item) => item.canvas.warnings ?? [])),
          ),
        );
        setDraftReviewed(false);
        setActiveStep(activeCanvas ? "generate" : restoredRouting.confirmed ? "review" : "sources");
        return;
      }
      try {
        const restoredCanvas = await getDraftLectureCanvas(
          targetWorkspace.courseId,
          targetWorkspace.lectureId,
          session,
        );
        setCanvas(restoredCanvas);
        setGeneratedLectureIds([targetWorkspace.lectureId]);
        setGenerationWarnings(restoredCanvas.warnings ?? []);
        setDraftReviewed(false);
        setActiveStep("generate");
      } catch (canvasError) {
        setActiveStep(restoredRouting.confirmed ? "review" : "sources");
        if (!options.quietDraftMiss) {
          setError(
            canvasError instanceof Error
              ? canvasError.message
              : "Could not restore professor preview.",
          );
        }
      }
    } catch (restoreError) {
      if (!options.skipWhenMissing) {
        setError(
          restoreError instanceof Error
            ? restoreError.message
            : "Could not refresh workspace state.",
        );
      }
    } finally {
      setIsRestoring(false);
    }
  }

  const defineStep = {
    courseSearchFailed,
    courseSuggestions,
    courseSourceStatuses: session.university_course_source_statuses,
    courseReady,
    isCreating: pendingAction === "create",
    isReady: setupReady,
    onCreate: () =>
      run("create", async () => {
        const schedule = setup.target === "full-course" ? lectureSchedule : [];
        const created = await createCourseWorkspace(setup, session, schedule);
        setWorkspace({ courseId: created.course.id, lectureId: created.active_lecture_id });
        setMediaLectureId(created.active_lecture_id);
        setWorkspaceCourse(created.course);
        setWorkspaceLectures(created.lectures);
        resetGeneratedState();
        const sourceBundle = await getSourceBundle(created.course.id, session);
        setSupportedUploads(sourceBundle.supported_uploads ?? []);
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
    pendingAction,
    setup,
    uploadFiles,
    supportedUploads,
    workspaceReady: Boolean(workspace),
    onUploadFilesChange: setUploadFiles,
    onScheduleChange: setLectureSchedule,
    onUpload: () =>
      run("upload", async () => {
        const activeWorkspace = requireWorkspace(workspace);
        const result = await uploadProfessorMaterials({
          courseId: activeWorkspace.courseId,
          files: uploadFiles,
          session,
          supportedUploads,
        });
        if (result.bundle) {
          setBundle(result.bundle);
          setSupportedUploads(result.bundle.supported_uploads ?? supportedUploads);
        }
        if (result.uploaded.length > 0 || result.mutationUncertain) {
          resetGeneratedState();
          if (setup.target === "full-course") setScheduleApplied(false);
        }
        if (result.error) throw result.error;
        if (setup.target === "full-course") {
          const proposal = await proposeLectureSchedule({
            courseId: activeWorkspace.courseId,
            count: Number(setup.lectureCount) || null,
            firstLectureDate: setup.firstLectureDate,
            session,
          });
          setLectureSchedule(proposal.lectures);
        }
        if (setup.target !== "full-course") {
          await sourceRouting.propose(activeWorkspace.courseId);
          setActiveStep("sources");
        }
        setUploadFiles([]);
        const ignoredText = ignoredUploadNotice(result.ignored);
        if (result.uploaded.length === 1) {
          return `Uploaded ${result.uploaded[0].path} as ${result.uploaded[0].kind}.${ignoredText}`;
        }
        return `Uploaded ${result.uploaded.length} materials into the source bundle.${ignoredText}`;
      }),
    onApplySchedule: () =>
      run("apply-schedule", async () => {
        const activeWorkspace = requireWorkspace(workspace);
        const created = await createCourseWorkspace(
          setup,
          session,
          lectureSchedule,
          activeWorkspace.courseId,
        );
        setWorkspace({ courseId: created.course.id, lectureId: created.active_lecture_id });
        setMediaLectureId(created.active_lecture_id);
        setWorkspaceCourse(created.course);
        setWorkspaceLectures(created.lectures);
        resetGeneratedState();
        setScheduleApplied(true);
        setActiveStep("sources");
        await sourceRouting.propose(created.course.id);
        return `Lecture schedule applied with ${created.lectures.length} dated lectures.`;
      }),
  };

  const generateStep = {
    canvas,
    canGenerate: Boolean(bundleReady && routingReady && reviewReady && workspace),
    generationProgress,
    generatedCount: generatedLectureIds.length,
    isFullCourse: setup.target === "full-course",
    isGenerating: pendingAction === "generate",
    retryingLectureIds,
    onContinueToPublish: () => {
      setDraftReviewed(true);
      setActiveStep("publish");
    },
    previewLectures:
      setup.target === "full-course"
        ? publishLectures
            .filter((lecture) => generatedLectureIds.includes(lecture.id))
            .map(({ id, label, previewHref: href }) => ({ id, label, previewHref: href }))
        : workspace && previewHref
          ? [
              {
                id: workspace.lectureId,
                label: `${lectureFromWorkspace(workspace, setup, lectureSchedule).number} · ${lectureFromWorkspace(workspace, setup, lectureSchedule).title}`,
                previewHref,
              },
            ]
          : [],
    totalCount: fullCourseLectureIds.length,
    onRetry: (lectureId: string) => void retryCanvas(lectureId),
    onGenerate: () =>
      run("generate", async () => {
        const activeWorkspace = requireWorkspace(workspace);
        await requireConfirmedRouting(activeWorkspace.courseId);
        const lectureIds =
          setup.target === "full-course" && fullCourseLectureIds.length
            ? fullCourseLectureIds
            : [activeWorkspace.lectureId];
        setDraftReviewed(false);
        setGenerationProgress(lectureIds.map((lectureId) => ({ lectureId, status: "pending" })));
        setGenerationWarnings([]);
        const canvases = await generateCanvases(activeWorkspace.courseId, lectureIds);
        if (!canvases) return;
        setCanvas(canvases[0] ?? null);
        setGeneratedLectureIds(lectureIds);
        setGenerationWarnings(Array.from(new Set(canvases.flatMap((item) => item.warnings ?? []))));
        if (lectureIds.length === 1)
          return "Course-builder agent generated a source-grounded canvas draft.";
        return `Course-builder agent generated ${lectureIds.length} source-grounded lecture canvases.`;
      }),
  };

  const mediaStep = {
    canContinue: Boolean(bundleReady && routingReady && workspace),
    canSearch: Boolean(setupReady && workspace),
    canSuggest: Boolean(suggestedQueries.length && setupReady && workspace),
    pendingAction,
    onContinue: () =>
      void run("validate-routing", async () => {
        const activeWorkspace = requireWorkspace(workspace);
        await requireConfirmedRouting(activeWorkspace.courseId);
        setAutoSuggesting(false);
        setMediaReviewed(true);
        setActiveStep("generate");
      }),
    onQueryChange: setQuery,
    onSearch: () =>
      run("search", async () => {
        const searchQuery = query.trim() || defaultYoutubeQuery;
        if (!query.trim()) setQuery(searchQuery);
        const activeWorkspace = requireWorkspace(workspace);
        const response = await searchYoutubeMedia(activeWorkspace.courseId, searchQuery, session);
        setVideos(response.items);
        return `Found ${response.items.length} YouTube candidates.`;
      }),
    onSuggest: () =>
      run("suggest-videos", async () => {
        const activeWorkspace = requireWorkspace(workspace);
        const count = await searchSuggestedVideos(activeWorkspace.courseId);
        setAutoSuggestedSearchKey(suggestedSearchKey || null);
        return `Found ${count} suggested YouTube candidates from ${suggestedQueries.length} searches.`;
      }),
    onTargetLectureChange: setMediaLectureId,
    onToggleVideo: (videoId: string) => {
      const activeWorkspace = requireWorkspace(workspace);
      const target = mediaTargetLecture ?? mediaTargetLectures[0];
      const video = availableVideos.find((candidate) => candidate.video_id === videoId);
      if (!target || !video) return;
      const wasSelected = selectedVideos.has(videoId);
      const nextSelected = toggleSelected(selectedVideos, videoId);
      mediaSelectionGeneration.current += 1;
      setSelectedVideos(nextSelected);
      void run("include-videos", async () => {
        try {
          if (wasSelected) {
            await removeYoutubeMedia({
              courseId: activeWorkspace.courseId,
              lectureId: target.id,
              videoId,
              session,
            });
          } else {
            await includeYoutubeMedia({
              courseId: activeWorkspace.courseId,
              lectureId: target.id,
              video,
              session,
            });
          }
        } catch (saveError) {
          setSelectedVideos((current) => toggleSelected(current, videoId));
          throw saveError;
        }
        setMediaIncluded(nextSelected.size > 0);
        setMediaReviewed(true);
        if (canvas) setCanvas(null);
        setGeneratedLectureIds([]);
        setGenerationProgress([]);
        setGenerationWarnings([]);
        if (wasSelected) return `Removed video from lecture ${target.number}.`;
        const selectedCount = nextSelected.size;
        return `Saved ${selectedCount} approved ${selectedCount === 1 ? "video" : "videos"} for lecture ${target.number}.`;
      });
    },
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
    onPublish: () =>
      run("publish", async () => {
        const activeWorkspace = requireWorkspace(workspace);
        const lectureIds =
          setup.target === "full-course"
            ? generatedLectureIds.length
              ? generatedLectureIds
              : fullCourseLectureIds
            : [activeWorkspace.lectureId];
        const published = [];
        for (const lectureId of lectureIds) {
          published.push(await onPublishWorkspace(activeWorkspace.courseId, lectureId));
        }
        onWorkspacePublished(
          workspaceCourse ?? courseFromSetup(activeWorkspace.courseId, setup, session),
          workspaceLectures.length
            ? workspaceLectures
            : activationLectures(activeWorkspace, setup, lectureSchedule),
        );
        const lastPublished = published[published.length - 1];
        const when = lastPublished?.published_at
          ? ` at ${new Date(lastPublished.published_at).toLocaleString()}`
          : "";
        if (published.length === 1)
          return `Tutor workspace published as version ${lastPublished.version ?? 1}${when}.`;
        return `${published.length} tutor workspaces published for students${when}.`;
      }),
    publishedCount: fullCoursePublishedCount,
    lectures: publishLectures,
    ready: workspacePublished,
    totalCount: fullCourseLectureIds.length,
  };

  const routingLectures = lectureSchedule.length
    ? lectureSchedule
    : workspaceLectures.map(scheduleItemFromLecture);
  const routingStep = {
    isSaving: pendingAction === "confirm-routing" || pendingAction === "regenerate-routing",
    lectures: routingLectures,
    routing: sourceRouting.routing,
    onRouteChange: sourceRouting.updateRoute,
    onRegenerate: () =>
      run("regenerate-routing", async () => {
        const activeWorkspace = requireWorkspace(workspace);
        await sourceRouting.regenerate(activeWorkspace.courseId);
        return "Source assignments rebuilt from the indexed course evidence.";
      }),
    onConfirm: () =>
      run("confirm-routing", async () => {
        const activeWorkspace = requireWorkspace(workspace);
        await sourceRouting.confirm(activeWorkspace.courseId);
        setActiveStep("review");
        return "Source assignments confirmed for Canvas generation.";
      }),
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
    routingStep,
    restoreWorkspace: () => void restoreFromBackend(workspace, { quietDraftMiss: true }),
    setActiveStep,
    steps,
    uploadStep,
    workspace,
  };
}

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;
  try {
    return await Promise.race([
      promise,
      new Promise<never>((_, reject) => {
        timeoutId = setTimeout(() => reject(new Error("Timed out.")), timeoutMs);
      }),
    ]);
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
  }
}
