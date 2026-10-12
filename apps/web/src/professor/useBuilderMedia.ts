import { useEffect, useEffectEvent, useRef, useState } from "react";

import { useI18n } from "../i18n/i18n";
import { hasCanvasVideo, toggleSelected } from "./ProfessorCourseBuilderParts";
import {
  includeYoutubeMedia,
  listYoutubeMedia,
  removeYoutubeMedia,
  searchYoutubeMedia,
} from "./professorApi";
import {
  isCourseSetupReady,
  type CourseSetup,
  type CourseWorkspaceState,
} from "./professorBuilderState";
import type { useProfessorWorkflowRun } from "./professorWorkflowRun";
import type { lectureFromWorkspace } from "./professorWorkspaceView";
import { requireWorkspace } from "./professorWorkspaceView";
import {
  flattenVideoGroups,
  type YoutubeCandidateGroup,
  youtubeSuggestionQueries,
} from "./professorYoutubeSuggestions";
import type {
  CanvasDocument,
  LoginSession,
  SourceBundleManifest,
  YoutubeVideoCandidate,
} from "../shared/types";

type Lecture = ReturnType<typeof lectureFromWorkspace>;

/** Optional lecture videos: automatic suggestions, search and saved selections. */
export function useBuilderMedia({
  session,
  initialQuery,
  setup,
  workspace,
  bundle,
  canvas,
  lectures,
  active,
  workflow,
  onContinue,
  onMediaChanged,
}: {
  session: LoginSession;
  initialQuery: string;
  setup: CourseSetup;
  workspace: CourseWorkspaceState | null;
  bundle: SourceBundleManifest | null;
  canvas: CanvasDocument | null;
  lectures: Lecture[];
  /** Automatic suggestions only run while the media stage is open. */
  active: boolean;
  workflow: ReturnType<typeof useProfessorWorkflowRun>;
  onContinue: () => Promise<void>;
  onMediaChanged: () => void;
}) {
  const { t } = useI18n();
  const { pendingAction, run, setError } = workflow;
  const [query, setQuery] = useState(initialQuery);
  const [videos, setVideos] = useState<YoutubeVideoCandidate[]>([]);
  const [suggestedGroups, setSuggestedGroups] = useState<YoutubeCandidateGroup[]>([]);
  const [selectedVideos, setSelectedVideos] = useState<Set<string>>(new Set());
  const [autoSuggestedKey, setAutoSuggestedKey] = useState<string | null>(null);
  const suggestionGeneration = useRef(0);
  const selectionGeneration = useRef(0);
  const [lectureId, setLectureId] = useState(workspace?.lectureId ?? "");
  const [included, setIncluded] = useState(false);
  const target = lectures.find((lecture) => lecture.id === lectureId) ?? lectures[0];
  const lectureKey = lectures.map((lecture) => lecture.id).join("|");
  const queries = youtubeSuggestionQueries(setup, target);
  const defaultQuery = queries[0] ?? setup.courseTitle.trim();
  const courseId = workspace?.courseId ?? "";
  const targetId = target?.id ?? "";
  const scopeKey = courseId && targetId ? `${courseId}:${targetId}` : "";
  const suggestionKey =
    workspace && queries.length
      ? [
          workspace.courseId,
          target?.id ?? "no-lecture",
          bundle?.files.map((file) => `${file.path}:${file.size_bytes}`).join(",") ?? "no-bundle",
          queries.join("|"),
        ].join("::")
      : "";
  const availableVideos = flattenVideoGroups([
    ...suggestedGroups,
    { query: query.trim() || defaultQuery, videos },
  ]);
  const setupReady = isCourseSetupReady(setup);
  const runAutomaticSearch = useEffectEvent(searchSuggested);

  useEffect(() => {
    if (!lectureKey) {
      if (lectureId) setLectureId("");
      return;
    }
    const ids = lectureKey.split("|");
    if (!ids.includes(lectureId)) setLectureId(ids[0]);
  }, [lectureId, lectureKey]);

  useEffect(() => {
    if (!scopeKey) return;
    suggestionGeneration.current += 1;
    const generation = ++selectionGeneration.current;
    setQuery(defaultQuery);
    setVideos([]);
    setSuggestedGroups([]);
    setSelectedVideos(new Set());
    setIncluded(false);
    setAutoSuggestedKey(null);
    void listYoutubeMedia({ courseId, lectureId: targetId, session })
      .then((selections) => {
        if (generation !== selectionGeneration.current) return;
        setSelectedVideos(new Set(selections.map((selection) => selection.video.video_id)));
        setIncluded(selections.length > 0);
      })
      .catch((loadError) => {
        if (generation === selectionGeneration.current) {
          setError(
            loadError instanceof Error ? loadError.message : "YouTube selections failed to load.",
          );
        }
      });
  }, [defaultQuery, courseId, scopeKey, targetId, session, setError]);

  useEffect(() => {
    if (
      !active ||
      !workspace ||
      !setupReady ||
      !suggestionKey ||
      pendingAction !== null ||
      autoSuggestedKey === suggestionKey
    )
      return;
    let cancelled = false;
    setAutoSuggestedKey(suggestionKey);
    setError(null);
    void runAutomaticSearch(workspace.courseId).catch((autoError) => {
      if (!cancelled)
        setError(autoError instanceof Error ? autoError.message : "YouTube suggestions failed.");
    });
    return () => {
      cancelled = true;
    };
  }, [active, autoSuggestedKey, pendingAction, setError, setupReady, suggestionKey, workspace]);

  async function searchSuggested(searchCourseId: string) {
    const generation = ++suggestionGeneration.current;
    const responses = await Promise.all(
      queries.map(async (searchQuery) => {
        try {
          const response = await withTimeout(
            searchYoutubeMedia(searchCourseId, searchQuery, session, 3),
            6000,
          );
          return { query: searchQuery, videos: response.items };
        } catch (error) {
          const message = error instanceof Error ? error.message : "Video search failed.";
          return { query: searchQuery, videos: [], error: message };
        }
      }),
    );
    const seen = new Set<string>();
    const groups: YoutubeCandidateGroup[] = responses.map((response) => ({
      query: response.query,
      videos: response.videos.filter(
        (video) => !seen.has(video.video_id) && seen.add(video.video_id),
      ),
      error: response.error,
    }));
    if (generation === suggestionGeneration.current) setSuggestedGroups(groups);
    return flattenVideoGroups(groups).length;
  }

  function toggleVideo(videoId: string) {
    const activeWorkspace = requireWorkspace(workspace);
    const video = availableVideos.find((candidate) => candidate.video_id === videoId);
    if (!target || !video) return;
    const wasSelected = selectedVideos.has(videoId);
    const nextSelected = toggleSelected(selectedVideos, videoId);
    selectionGeneration.current += 1;
    setSelectedVideos(nextSelected);
    void run("include-videos", async () => {
      const selection = { courseId: activeWorkspace.courseId, lectureId: target.id, session };
      try {
        if (wasSelected) await removeYoutubeMedia({ ...selection, videoId });
        else await includeYoutubeMedia({ ...selection, video });
      } catch (saveError) {
        setSelectedVideos((current) => toggleSelected(current, videoId));
        throw saveError;
      }
      setIncluded(nextSelected.size > 0);
      onMediaChanged();
      if (wasSelected) return t("builder.status.videoRemoved", { lecture: target.number });
      return nextSelected.size === 1
        ? t("builder.status.videoSavedOne", { lecture: target.number })
        : t("builder.status.videoSavedMany", { count: nextSelected.size, lecture: target.number });
    });
  }

  return {
    ready: included || selectedVideos.size > 0 || hasCanvasVideo(canvas),
    query,
    setQuery,
    reset() {
      setVideos([]);
      setSuggestedGroups([]);
      suggestionGeneration.current += 1;
      selectionGeneration.current += 1;
      setAutoSuggestedKey(null);
      setSelectedVideos(new Set());
      setIncluded(false);
    },
    selectLecture: setLectureId,
    step: {
      canSearch: Boolean(setupReady && workspace),
      canSuggest: Boolean(queries.length && setupReady && workspace),
      pendingAction,
      onContinue: () => void run("validate-routing", onContinue),
      onQueryChange: setQuery,
      onSearch: () =>
        run("search", async () => {
          const searchQuery = query.trim() || defaultQuery;
          if (!query.trim()) setQuery(searchQuery);
          const activeWorkspace = requireWorkspace(workspace);
          const response = await searchYoutubeMedia(activeWorkspace.courseId, searchQuery, session);
          setVideos(response.items);
          return t("builder.status.videosFound", { count: response.items.length });
        }),
      onSuggest: () =>
        run("suggest-videos", async () => {
          const count = await searchSuggested(requireWorkspace(workspace).courseId);
          setAutoSuggestedKey(suggestionKey || null);
          return t("builder.status.videosSuggested", { count, searches: queries.length });
        }),
      onTargetLectureChange: setLectureId,
      onToggleVideo: toggleVideo,
      query,
      selectedVideos,
      suggestedGroups,
      suggestedQueries: queries,
      targetLectureId: lectureId,
      targetLectures: lectures,
      videos,
    },
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
