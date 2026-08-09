import { useState } from "react";

import type { CourseWorkspaceGroup } from "./dashboardCourses";
import { availableCourseLectures } from "./dashboardCourses";
import { DashboardLectureRow } from "./DashboardLectureRow";
import {
  CourseWorkspaceTabs,
  panelId,
  tabId,
  type CourseWorkspaceTool,
} from "./CourseWorkspaceTabs";
import { ExamReadinessPanel } from "./ExamReadinessPanel";
import { useI18n } from "./i18n";
import { PracticeExamPanel } from "./PracticeExamPanel";
import type { Attendance, Lecture, LoginSession } from "./types";

const LECTURE_PREVIEW_COUNT = 2;

export function DashboardCourseWorkspaces({
  courseGroups,
  session,
  onOpen,
  onProgress,
  onSetAttendance,
}: {
  courseGroups: CourseWorkspaceGroup[];
  session: LoginSession | null;
  onOpen: (lecture: Lecture) => void;
  onProgress: () => void | Promise<void>;
  onSetAttendance: (lectureId: string, attendance: Attendance) => void;
}) {
  const { t } = useI18n();
  const [selectedCourseId, setSelectedCourseId] = useState<string | null>(null);
  const [activeTool, setActiveTool] = useState<CourseWorkspaceTool>("lectures");
  const [expandedLectureLists, setExpandedLectureLists] = useState<Record<string, boolean>>({});
  const availableGroups = courseGroups.filter((group) => group.tutorAvailable);
  const unavailableGroups = courseGroups.filter((group) => !group.tutorAvailable);
  const activeGroup =
    availableGroups.find((group) => group.course.id === selectedCourseId) ?? availableGroups[0];

  function selectCourse(courseId: string) {
    setSelectedCourseId(courseId);
    setActiveTool("lectures");
  }

  return (
    <>
      {availableGroups.length ? (
        <section aria-label={t("dashboard.availableWorkspaces")} className="available-workspaces">
          <div className="course-card-grid" role="list">
            {availableGroups.map((group) => {
              const selected = group.course.id === activeGroup?.course.id;
              return (
                <div key={group.course.id} role="listitem">
                  <button
                    aria-label={t("dashboard.openWorkspace", { course: group.course.title })}
                    aria-pressed={selected}
                    className={`course-card${selected ? " is-selected" : ""}`}
                    type="button"
                    onClick={() => selectCourse(group.course.id)}
                  >
                    <span className="course-card-copy">
                      <span className="course-card-title-line">
                        <span className="course-card-title" role="heading" aria-level={4}>
                          {group.course.title}
                        </span>
                        <CourseSourceTags sources={group.sources} />
                      </span>
                      <span>{group.course.professor}</span>
                    </span>
                    <span className="course-card-meta">
                      {t("dashboard.publishedLectures", { count: group.courseLectures.length })}
                    </span>
                  </button>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {activeGroup ? (
        <ActiveWorkspace
          activeTool={activeTool}
          expanded={expandedLectureLists[activeGroup.course.id] ?? false}
          group={activeGroup}
          session={session}
          onActiveToolChange={setActiveTool}
          onOpen={onOpen}
          onProgress={onProgress}
          onSetAttendance={onSetAttendance}
          onToggleLectures={() =>
            setExpandedLectureLists((current) => ({
              ...current,
              [activeGroup.course.id]: !current[activeGroup.course.id],
            }))
          }
        />
      ) : null}

      {unavailableGroups.length ? <UnavailableCourses groups={unavailableGroups} /> : null}
    </>
  );
}

function ActiveWorkspace({
  activeTool,
  expanded,
  group,
  session,
  onActiveToolChange,
  onOpen,
  onProgress,
  onSetAttendance,
  onToggleLectures,
}: {
  activeTool: CourseWorkspaceTool;
  expanded: boolean;
  group: CourseWorkspaceGroup;
  session: LoginSession | null;
  onActiveToolChange: (tool: CourseWorkspaceTool) => void;
  onOpen: (lecture: Lecture) => void;
  onProgress: () => void | Promise<void>;
  onSetAttendance: (lectureId: string, attendance: Attendance) => void;
  onToggleLectures: () => void;
}) {
  const { t } = useI18n();
  const idBase = `course-tools-${group.course.id.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
  const visibleLectures = expanded
    ? group.courseLectures
    : group.courseLectures.slice(0, LECTURE_PREVIEW_COUNT);

  return (
    <section
      aria-label={t("dashboard.studyWorkspaceFor", { course: group.course.title })}
      className="course-workspace-body"
      role="region"
    >
      <header className="workspace-toolbar">
        <h3>{t("dashboard.studyTools")}</h3>
        <CourseWorkspaceTabs
          activeTool={activeTool}
          idBase={idBase}
          onChange={onActiveToolChange}
        />
      </header>

      <div
        aria-labelledby={tabId(idBase, "lectures")}
        className="workspace-tab-panel"
        hidden={activeTool !== "lectures"}
        id={panelId(idBase, "lectures")}
        role="tabpanel"
      >
        <div
          aria-label={t("dashboard.availableLectures", { course: group.course.title })}
          className="lecture-list"
        >
          {visibleLectures.map((lecture) => (
            <DashboardLectureRow
              key={lecture.id}
              lecture={lecture}
              onOpen={onOpen}
              onSetAttendance={onSetAttendance}
            />
          ))}
        </div>
        {group.courseLectures.length > LECTURE_PREVIEW_COUNT ? (
          <button className="lecture-list-toggle" type="button" onClick={onToggleLectures}>
            {expanded
              ? t("dashboard.showFirstLectures", { count: LECTURE_PREVIEW_COUNT })
              : t("dashboard.showAllLectures", { count: group.courseLectures.length })}
          </button>
        ) : null}
      </div>

      <div
        aria-labelledby={tabId(idBase, "readiness")}
        className="workspace-tab-panel"
        hidden={activeTool !== "readiness"}
        id={panelId(idBase, "readiness")}
        role="tabpanel"
      >
        <ExamReadinessPanel
          course={group.course}
          lectures={availableCourseLectures(group.courseLectures)}
          session={session}
          onOpenLecture={onOpen}
          onProgress={onProgress}
        />
      </div>

      <div
        aria-labelledby={tabId(idBase, "practice")}
        className="workspace-tab-panel"
        hidden={activeTool !== "practice"}
        id={panelId(idBase, "practice")}
        role="tabpanel"
      >
        <PracticeExamPanel course={group.course} session={session} />
      </div>
    </section>
  );
}

function UnavailableCourses({ groups }: { groups: CourseWorkspaceGroup[] }) {
  const { t } = useI18n();
  return (
    <details className="unavailable-courses">
      <summary>
        <span>{t("dashboard.otherCourses")}</span>
        <span>{t("dashboard.otherCoursesCount", { count: groups.length })}</span>
      </summary>
      <div className="unavailable-courses-body">
        <p>{t("dashboard.otherCoursesHelp")}</p>
        <ul>
          {groups.map((group) => (
            <li className="unavailable-course" key={group.course.id}>
              <h4>{group.course.title}</h4>
              <CourseSourceTags sources={group.sources} />
            </li>
          ))}
        </ul>
      </div>
    </details>
  );
}

function CourseSourceTags({ sources }: { sources: CourseWorkspaceGroup["sources"] }) {
  const { t } = useI18n();
  if (!sources.length) return null;
  return (
    <span aria-label={t("dashboard.courseSources")} className="course-source-tags">
      {sources.map((source) => (
        <span className="course-source-tag" key={source}>
          {source === "alma" ? "Alma" : "ILIAS"}
        </span>
      ))}
    </span>
  );
}
