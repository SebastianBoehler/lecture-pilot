import { lazy, Suspense, useState } from "react";

import { CourseSearch } from "./CourseSearch";
import {
  CourseWorkspaceTabs,
  panelId,
  tabId,
  type CourseWorkspaceTool,
} from "./CourseWorkspaceTabs";
import type { CourseWorkspaceGroup } from "./dashboardCourses";
import { availableCourseLectures } from "./dashboardCourses";
import { courseProgress, previewLectures } from "./dashboardLectureProgress";
import { DashboardLectureRow } from "./DashboardLectureRow";
import { useI18n } from "../i18n/i18n";
import type { Attendance, LearnerCourseProfile, Lecture, LoginSession } from "../shared/types";

const ExamPrepPanel = lazy(() =>
  import("../exam/ExamPrepPanel").then((module) => ({ default: module.ExamPrepPanel })),
);

const LECTURE_PREVIEW_COUNT = 2;

export function DashboardActiveWorkspace({
  activeTool,
  expanded,
  group,
  newLectureIds,
  profile,
  session,
  onActiveToolChange,
  onOpen,
  onOpenSection,
  onProgress,
  onSetAttendance,
  onToggleLectures,
}: {
  activeTool: CourseWorkspaceTool;
  expanded: boolean;
  group: CourseWorkspaceGroup;
  newLectureIds: Set<string>;
  profile?: LearnerCourseProfile;
  session: LoginSession | null;
  onActiveToolChange: (tool: CourseWorkspaceTool) => void;
  onOpen: (lecture: Lecture) => void;
  onOpenSection: (lecture: Lecture, sectionId: string) => void;
  onProgress: () => void | Promise<void>;
  onSetAttendance: (lectureId: string, attendance: Attendance) => void;
  onToggleLectures: () => void;
}) {
  const { t } = useI18n();
  const [examOpened, setExamOpened] = useState(false);
  const idBase = `course-tools-${group.course.id.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
  const lectures = group.courseLectures;
  const available = availableCourseLectures(lectures);
  const preview = previewLectures(lectures, LECTURE_PREVIEW_COUNT);
  const visibleLectures = expanded ? lectures : preview;
  const progress = courseProgress(lectures, profile);

  return (
    <section
      aria-label={t("dashboard.studyWorkspaceFor", { course: group.course.title })}
      className="course-workspace-body"
      role="region"
    >
      <header className="workspace-toolbar">
        <div className="workspace-title">
          <h3>{group.course.title}</h3>
          {profile && progress.total ? (
            <p className="workspace-progress">
              <span
                aria-hidden="true"
                className="workspace-progress-bar"
                style={{ ["--progress" as string]: `${progress.percent}%` }}
              />
              {t("dashboard.progress.course", {
                percent: progress.percent,
                passed: progress.passed,
                total: progress.total,
              })}
            </p>
          ) : null}
        </div>
        <CourseWorkspaceTabs
          activeTool={activeTool}
          idBase={idBase}
          onChange={(tool) => {
            if (tool === "exam") setExamOpened(true);
            onActiveToolChange(tool);
          }}
        />
      </header>

      <div
        aria-labelledby={tabId(idBase, "lectures")}
        className="workspace-tab-panel"
        hidden={activeTool !== "lectures"}
        id={panelId(idBase, "lectures")}
        role="tabpanel"
      >
        {session && available.length ? (
          <CourseSearch
            course={group.course}
            lectures={available}
            session={session}
            onOpenSection={onOpenSection}
          />
        ) : null}
        <div
          aria-label={t("dashboard.availableLectures", { course: group.course.title })}
          className="lecture-list"
        >
          {visibleLectures.map((lecture) => (
            <DashboardLectureRow
              isNew={newLectureIds.has(lecture.id)}
              key={lecture.id}
              lecture={lecture}
              progress={progress.byLecture.get(lecture.id)}
              onOpen={onOpen}
              onSetAttendance={onSetAttendance}
            />
          ))}
        </div>
        {lectures.length > preview.length ? (
          <button className="lecture-list-toggle" type="button" onClick={onToggleLectures}>
            {expanded
              ? t("dashboard.showLatestLectures")
              : t("dashboard.showAllLectures", { count: lectures.length })}
          </button>
        ) : null}
      </div>

      <div
        aria-labelledby={tabId(idBase, "exam")}
        className="workspace-tab-panel"
        hidden={activeTool !== "exam"}
        id={panelId(idBase, "exam")}
        role="tabpanel"
      >
        {examOpened || activeTool === "exam" ? (
          <Suspense fallback={<p role="status">{t("app.loadingView")}</p>}>
            <ExamPrepPanel
              course={group.course}
              lectures={available}
              session={session}
              onOpenLecture={onOpen}
              onProgress={onProgress}
            />
          </Suspense>
        ) : null}
      </div>
    </section>
  );
}
