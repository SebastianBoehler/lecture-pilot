import { useState } from "react";

import type { CourseSetup, SavedProfessorFlow } from "./professorBuilderState";
import { publishLectureRows } from "./professorPublishRows";
import {
  activationLectures,
  courseFromSetup,
  scheduleItemFromLecture,
} from "./professorWorkspaceActivation";
import { lectureFromWorkspace } from "./professorWorkspaceView";
import type {
  CourseMaterialUploadType,
  CourseWorkspaceResult,
  LoginSession,
  SourceBundleManifest,
  UniversityCourse,
} from "./types";
import type { RestoredWorkspace } from "./useBuilderRestore";

type WorkspaceLecture = ReturnType<typeof lectureFromWorkspace>;

/** The course being built: setup, workspace, sources, schedule and publication state. */
export function useBuilderWorkspace({
  savedFlow,
  session,
  previewWorkspaceUrl,
}: {
  savedFlow: SavedProfessorFlow;
  session: LoginSession;
  previewWorkspaceUrl: (courseId: string, lecture: WorkspaceLecture) => string;
}) {
  const [setup, setSetup] = useState(savedFlow.setup);
  const [workspace, setWorkspace] = useState(savedFlow.workspace);
  const [workspaceCourse, setWorkspaceCourse] = useState<UniversityCourse | null>(null);
  const [workspaceLectures, setWorkspaceLectures] = useState<WorkspaceLecture[]>([]);
  const [courseReady, setCourseReady] = useState(savedFlow.courseReady && !!savedFlow.workspace);
  const [bundle, setBundle] = useState<SourceBundleManifest | null>(null);
  const [supportedUploads, setSupportedUploads] = useState<CourseMaterialUploadType[]>([]);
  const [lectureSchedule, setLectureSchedule] = useState(savedFlow.lectureSchedule);
  const [scheduleApplied, setScheduleApplied] = useState(setup.target !== "full-course");
  // Publication state of this builder's own course (not the learner workspace course).
  const [coursePublished, setCoursePublished] = useState({ courseId: "", ids: [] as string[] });
  const fullCourse = setup.target === "full-course";
  const targetLectures = workspace
    ? fullCourse
      ? workspaceLectures.length
        ? workspaceLectures
        : activationLectures(workspace, setup, lectureSchedule)
      : [lectureFromWorkspace(workspace, setup, lectureSchedule)]
    : [];
  const targetIds = targetLectures.map((lecture) => lecture.id);
  const publishedIds =
    workspace && coursePublished.courseId === workspace.courseId ? coursePublished.ids : [];
  const publishedCount = targetIds.filter((id) => publishedIds.includes(id)).length;
  const workspaceLecture = workspace
    ? lectureFromWorkspace(workspace, setup, lectureSchedule)
    : null;
  const publishLectures =
    workspace && workspaceLecture
      ? publishLectureRows({
          courseId: workspace.courseId,
          lectureSchedule: workspaceLectures.length
            ? workspaceLectures.map(scheduleItemFromLecture)
            : lectureSchedule,
          previewWorkspaceUrl,
          publishedLectureIds: publishedIds,
          setup,
          workspaceLecture,
        })
      : [];

  return {
    setup,
    workspace,
    workspaceCourse,
    workspaceLectures,
    courseReady,
    bundle,
    bundleReady: Boolean(bundle?.files.length),
    supportedUploads,
    lectureSchedule,
    scheduleApplied,
    fullCourse,
    targetLectures,
    targetIds,
    workspaceLecture,
    publishedCount,
    published: Boolean(
      workspace &&
      (fullCourse
        ? targetIds.length > 0 && publishedCount === targetIds.length
        : publishedIds.includes(workspace.lectureId)),
    ),
    publishLectures,
    /** Draft previews: every generated lecture, or the single lecture once it has a canvas. */
    previewLectures(generatedIds: readonly string[], hasCanvas: boolean) {
      if (fullCourse) {
        return publishLectures
          .filter((lecture) => generatedIds.includes(lecture.id))
          .map(({ id, label, previewHref }) => ({ id, label, previewHref }));
      }
      if (!workspace || !workspaceLecture || !hasCanvas) return [];
      return [
        {
          id: workspace.lectureId,
          label: `${workspaceLecture.number} · ${workspaceLecture.title}`,
          previewHref: previewWorkspaceUrl(workspace.courseId, workspaceLecture),
        },
      ];
    },
    setSupportedUploads,
    setLectureSchedule,
    setScheduleApplied,
    markCourseReady: () => setCourseReady(true),
    /** A changed setup starts over: the previous workspace no longer applies. */
    clear(nextSetup: CourseSetup) {
      setSetup(nextSetup);
      setWorkspace(null);
      setWorkspaceCourse(null);
      setWorkspaceLectures([]);
      setCourseReady(false);
      setBundle(null);
      setSupportedUploads([]);
      setLectureSchedule([]);
      setScheduleApplied(nextSetup.target !== "full-course");
    },
    created(result: CourseWorkspaceResult) {
      setWorkspace({ courseId: result.course.id, lectureId: result.active_lecture_id });
      setWorkspaceCourse(result.course);
      setWorkspaceLectures(result.lectures);
    },
    bundleChanged(nextBundle: SourceBundleManifest) {
      setBundle(nextBundle);
      setSupportedUploads((current) => nextBundle.supported_uploads ?? current);
    },
    restored(courseId: string, restored: Partial<RestoredWorkspace>) {
      if (restored.publishedLectureIds) {
        setCoursePublished({ courseId, ids: restored.publishedLectureIds });
      }
      if (restored.bundle) {
        setBundle(restored.bundle);
        setSupportedUploads(restored.bundle.supported_uploads ?? []);
      }
      const lectures = restored.lectures;
      if (!lectures) return;
      setWorkspaceLectures(lectures);
      setWorkspaceCourse((current) => current ?? courseFromSetup(courseId, setup, session));
      if (fullCourse && !lectureSchedule.length) {
        setLectureSchedule(lectures.map(scheduleItemFromLecture));
      }
      if (fullCourse) setScheduleApplied(lectures.length > 0);
    },
    lecturePublished(courseId: string, lectureId: string) {
      setCoursePublished((current) => ({
        courseId,
        ids: [...(current.courseId === courseId ? current.ids : []), lectureId],
      }));
    },
  };
}
