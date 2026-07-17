import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";

import { getCourseLectures, getDraftLectureCanvas } from "./api";
import { draftLectureCanvas } from "./canvasDraftApi";
import { builderSteps, initialBuilderStep, type BuilderStep } from "./ProfessorBuilderStepper";
import {
  CanvasGenerationBatchError,
  generateLectureCanvasDrafts,
  type CanvasGenerationProgress,
} from "./professorCanvasGeneration";
import { hasCanvasVideo, toggleSelected } from "./ProfessorCourseBuilderParts";
import {
  createCourseWorkspace,
  getSourceBundle,
  includeYoutubeMedia,
  listYoutubeMedia,
  proposeLectureSchedule,
  removeYoutubeMedia,
  searchYoutubeMedia,
} from "./professorApi";
import {
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
import { universityCourseTitles } from "./professorCourseSuggestions";
import { useCourseTitleSuggestions } from "./useCourseTitleSuggestions";
import { useProfessorWorkflowRun } from "./professorWorkflowRun";
import { lectureFromWorkspace, requireWorkspace } from "./professorWorkspaceView";
import { uploadProfessorMaterials } from "./professorMaterialUpload";
import { ignoredUploadNotice } from "./professorUpload";
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
  const [lectureSchedule, setLectureSchedule] = useState<LectureScheduleItem[]>(
    savedFlow.lectureSchedule,
  );
  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [canvas, setCanvas] = useState<CanvasDocument | null>(null);
  const [generatedLectureIds, setGeneratedLectureIds] = useState<string[]>([]);
  const [draftReviewed, setDraftReviewed] = useState(false);
  const [generationProgress, setGenerationProgress] = useState<CanvasGenerationProgress[]>([]);
  const [generationWarnings, setGenerationWarnings] = useState<string[]>([]);
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
  const { error, notice, pendingAction, run, setError } = useProfessorWorkflowRun();
  const [restored, setRestored] = useState(!savedFlow.bundleReady && !savedFlow.canvasReady);
  const [isRestoring, setIsRestoring] = useState(false);
  const restoreGeneratedState = useEffectEvent(restoreFromBackend);
  const runAutomaticVideoSearch = useEffectEvent(searchSuggestedVideos);

  const setupReady = isCourseSetupReady(setup);
  const personalCourseTitles = useMemo(
    () => universityCourseTitles(session.university_courses ?? [], session.term),
    [session.term, session.university_courses],
  );
  const { courseSearchFailed, courseSuggestions } = useCourseTitleSuggestions({
    enabled: activeStep === "define" && !courseReady,
    personalTitles: personalCourseTitles,
    query: setup.courseTitle,
    session,
  });
  const bundleReady = Boolean(bundle?.files.length);
  const mediaReady = mediaIncluded || selectedVideos.size > 0 || hasCanvasVideo(canvas);
  const reviewReady = mediaReady || mediaReviewed;
  const reviewAvailable = bundleReady && (setup.target !== "full-course" || scheduleApplied);
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
    setLectureSchedule([]);
    setMediaLectureId("");
    setScheduleApplied(nextSetup.target !== "full-course");
    setActiveStep("define");
  }

  function resetGeneratedState() {
    setCanvas(null);
    setGeneratedLectureIds([]);
    setDraftReviewed(false);
    setGenerationProgress([]);
    setGenerationWarnings([]);
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

  async function generateCanvases(courseId: string, lectureIds: string[]) {
    try {
      return await generateLectureCanvasDrafts({
        lectureIds,
        draft: (lectureId) => draftLectureCanvas(courseId, lectureId, session),
        onDraftReady: recordGeneratedCanvas,
        onProgress: updateGenerationItem,
      });
    } catch (generationError) {
      if (generationError instanceof CanvasGenerationBatchError) return null;
      throw generationError;
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
      const restoredBundle = await getSourceBundle(targetWorkspace.courseId, session);
      setBundle(restoredBundle);
      const restoredLectures = await getCourseLectures(targetWorkspace.courseId, session);
      setWorkspaceLectures(restoredLectures);
      setWorkspaceCourse(
        (current) => current ?? courseFromSetup(targetWorkspace.courseId, setup, session),
      );
      if (setup.target === "full-course" && !lectureSchedule.length) {
        setLectureSchedule(restoredLectures.map(scheduleItemFromLecture));
      }
      try {
        const restoredCanvas = await getDraftLectureCanvas(
          targetWorkspace.courseId,
          targetWorkspace.lectureId,
          session,
        );
        setCanvas(restoredCanvas);
        setGeneratedLectureIds(
          setup.target === "full-course"
            ? restoredLectures.map((lecture) => lecture.id)
            : [targetWorkspace.lectureId],
        );
        setGenerationWarnings(restoredCanvas.warnings ?? []);
        setDraftReviewed(false);
        setActiveStep("generate");
      } catch (canvasError) {
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
        });
        if (result.bundle) setBundle(result.bundle);
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
        if (setup.target !== "full-course") setActiveStep("review");
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
    onRetry: (lectureId: string) =>
      run("generate", async () => {
        const activeWorkspace = requireWorkspace(workspace);
        const canvases = await generateCanvases(activeWorkspace.courseId, [lectureId]);
        if (!canvases) return;
        return `${lectureId.replace("lecture-", "Lecture ")} canvas is ready to review.`;
      }),
    onGenerate: () =>
      run("generate", async () => {
        const activeWorkspace = requireWorkspace(workspace);
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
    canContinue: Boolean(bundleReady && workspace),
    canSearch: Boolean(setupReady && workspace),
    canSuggest: Boolean(suggestedQueries.length && setupReady && workspace),
    pendingAction,
    onContinue: () => {
      setAutoSuggesting(false);
      setMediaReviewed(true);
      setActiveStep("generate");
    },
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
        return wasSelected
          ? `Removed video from lecture ${target.number}.`
          : `Saved 1 approved video for lecture ${target.number}.`;
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
