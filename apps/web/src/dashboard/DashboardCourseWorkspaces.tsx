import { useState } from "react";

import type { CourseWorkspaceTool } from "./CourseWorkspaceTabs";
import { DashboardActiveWorkspace } from "./DashboardActiveWorkspace";
import type { CourseWorkspaceGroup } from "./dashboardCourses";
import { useI18n } from "../i18n/i18n";
import type { Attendance, LearnerCourseProfile, Lecture, LoginSession } from "../shared/types";

export function DashboardCourseWorkspaces({
  courseGroups,
  newLectureIds,
  profileCourses,
  selectedCourseId,
  session,
  onSelectCourse,
  onOpen,
  onOpenSection,
  onProgress,
  onSetAttendance,
}: {
  courseGroups: CourseWorkspaceGroup[];
  newLectureIds: Set<string>;
  /** Undefined while the learner profile is unavailable; progress is then hidden. */
  profileCourses?: LearnerCourseProfile[];
  selectedCourseId: string;
  session: LoginSession | null;
  onSelectCourse: (courseId: string) => void;
  onOpen: (courseId: string, lecture: Lecture) => void;
  onOpenSection: (courseId: string, lecture: Lecture, sectionId: string) => void;
  onProgress: () => void | Promise<void>;
  onSetAttendance: (courseId: string, lectureId: string, attendance: Attendance) => void;
}) {
  const { t } = useI18n();
  const [activeTool, setActiveTool] = useState<CourseWorkspaceTool>("lectures");
  const [expandedLectureLists, setExpandedLectureLists] = useState<Record<string, boolean>>({});
  const availableGroups = courseGroups.filter((group) => group.tutorAvailable);
  const unavailableGroups = courseGroups.filter((group) => !group.tutorAvailable);
  const activeGroup =
    availableGroups.find((group) => group.course.id === selectedCourseId) ?? availableGroups[0];

  function selectCourse(courseId: string) {
    onSelectCourse(courseId);
    setActiveTool("lectures");
  }

  return (
    <>
      {availableGroups.length > 1 ? (
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
                        <span className="course-card-title">{group.course.title}</span>
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
        <DashboardActiveWorkspace
          key={activeGroup.course.id}
          activeTool={activeTool}
          expanded={expandedLectureLists[activeGroup.course.id] ?? false}
          group={activeGroup}
          newLectureIds={newLectureIds}
          profile={
            profileCourses
              ? (profileCourses.find((item) => item.course_id === activeGroup.course.id) ?? {
                  course_id: activeGroup.course.id,
                  memory: "",
                  passed_lecture_ids: [],
                  files: [],
                })
              : undefined
          }
          session={session}
          onActiveToolChange={setActiveTool}
          onOpen={(lecture) => onOpen(activeGroup.course.id, lecture)}
          onOpenSection={(lecture, sectionId) =>
            onOpenSection(activeGroup.course.id, lecture, sectionId)
          }
          onProgress={onProgress}
          onSetAttendance={(lectureId, attendance) =>
            onSetAttendance(activeGroup.course.id, lectureId, attendance)
          }
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
