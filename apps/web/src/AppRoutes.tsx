import { CourseLinkView } from "./CourseLinkView";
import { rememberReturnPath } from "./returnPath";
import { clearSavedFlow, writeResumeFlow } from "./professorBuilderState";
import { lazy, Suspense, type ReactNode } from "react";

import { courseUpdatePath, type AppRoute } from "./appRoute";
import { CourseManagementAccessRequired } from "./CourseManagementAccessRequired";
import { Dashboard } from "./Dashboard";
import { draftPreviewUrl } from "./draftPreviewUrl";
import { LoginView } from "./LoginView";
import { localDemoSession } from "./appDefaults";
import { ProfileView } from "./ProfileView";
import { useI18n } from "./i18n";
import type { CourseWorkspace } from "./useCourseWorkspace";
import { useLearnerProfile } from "./useLearnerProfile";
import type { LessonSession } from "./useLessonSession";
import type {
  Attendance,
  CanvasPublicationResult,
  Lecture,
  LoginSession,
  UniversityCourse,
  View,
} from "./types";

const InfoPage = lazy(() => import("./InfoPage").then((module) => ({ default: module.InfoPage })));
const ChangelogPage = lazy(() =>
  import("./ChangelogPage").then((module) => ({ default: module.ChangelogPage })),
);
const LessonWorkspace = lazy(() =>
  import("./LessonWorkspace").then((module) => ({ default: module.LessonWorkspace })),
);
const ProfessorCourseBuilder = lazy(() =>
  import("./ProfessorCourseBuilder").then((module) => ({ default: module.ProfessorCourseBuilder })),
);
const ProfessorCourseManagement = lazy(() =>
  import("./ProfessorCourseManagement").then((module) => ({
    default: module.ProfessorCourseManagement,
  })),
);
const ProfessorCoursePerformance = lazy(() =>
  import("./ProfessorPerformanceDashboard").then((module) => ({
    default: module.ProfessorPerformanceDashboard,
  })),
);
const ProfessorUsage = lazy(() =>
  import("./ProfessorUsage").then((module) => ({ default: module.ProfessorUsage })),
);

type AppRoutesProps = {
  workspace: CourseWorkspace;
  lesson: LessonSession;
  courseManagerSession: LoginSession | null;
  restoringSession: boolean;
  route: AppRoute;
  session: LoginSession | null;
  view: View;
  onLogout: () => void;
  onLogin: (session: LoginSession) => void;
  onNavigatePath: (path: string) => void;
  onOpenDemo: () => void;
  onOpenProfessorDemo: () => void;
  onOpenCourseLink: (courseId: string) => void;
  onPublishWorkspace: (courseId: string, lectureId: string) => Promise<CanvasPublicationResult>;
  onSetAttendance: (lectureId: string, attendance: Attendance) => void;
  onViewChange: (view: View) => void;
  onWorkspaceDeleted: (courseId: string) => void;
  onWorkspacePublished: (course: UniversityCourse, lectures: Lecture[]) => void;
};

export function AppRoutes(props: AppRoutesProps) {
  const { courseManagerSession, lesson, restoringSession, route, session, view, workspace } = props;
  const learnerProfileEnabled = Boolean(
    !restoringSession &&
    session?.roles?.includes("student") &&
    (view === "dashboard" || view === "profile"),
  );
  const learnerProfileState = useLearnerProfile(session, learnerProfileEnabled);

  if (restoringSession) return <ViewLoadingState />;
  if (route.view === "course-link") {
    return (
      <CourseLinkView
        code={route.code}
        courseId={route.courseId}
        session={session}
        onOpenCourse={props.onOpenCourseLink}
        onSignIn={(returnPath) => {
          rememberReturnPath(returnPath);
          props.onViewChange("login");
        }}
      />
    );
  }
  // A course manager on the login route is being forwarded once their courses are known.
  if (view === "login" && courseManagerSession) return <ViewLoadingState />;
  if (view === "login") {
    return (
      <LoginView
        onLogin={props.onLogin}
        onOpenDemo={props.onOpenDemo}
        onOpenProfessorDemo={props.onOpenProfessorDemo}
      />
    );
  }
  if (view === "dashboard") {
    return (
      <Dashboard
        lectures={workspace.lectures}
        publishedLectureIds={workspace.publishedLectureIds}
        learnerProfileState={learnerProfileState}
        session={session}
        workspaceCourse={workspace.course}
        workspaceLoadError={workspace.loadError}
        onOpen={(courseId, lecture, review) => {
          void lesson.openLecture(courseId, lecture, "learner", true, review);
        }}
        onSetAttendance={props.onSetAttendance}
      />
    );
  }
  if (view === "profile" && session) {
    return (
      <ProfileView
        learnerProfileState={learnerProfileEnabled ? learnerProfileState : undefined}
        onLogout={props.onLogout}
        session={session}
      />
    );
  }
  if (view === "professor" && courseManagerSession) {
    return deferred(
      <ProfessorCourseBuilder
        session={courseManagerSession}
        onPublishWorkspace={props.onPublishWorkspace}
        onWorkspacePublished={props.onWorkspacePublished}
        previewWorkspaceUrl={draftPreviewUrl}
      />,
    );
  }
  if (view === "course-management" && courseManagerSession) {
    return deferred(
      <ProfessorCourseManagement
        onCreateCourse={() => {
          clearSavedFlow();
          props.onViewChange("professor");
        }}
        onResumeCourse={(workspace) => {
          writeResumeFlow(workspace);
          props.onViewChange("professor");
        }}
        onCloseCourseUpdate={() => props.onViewChange("course-management")}
        onPreviewLecture={(courseId, lecture) => {
          void lesson.openLecture(courseId, lecture, "professor-preview");
        }}
        onUpdateCourse={(courseId) => props.onNavigatePath(courseUpdatePath(courseId))}
        session={courseManagerSession}
        updateCourseId={route.view === "course-management" ? route.updateCourseId : undefined}
        onWorkspaceDeleted={props.onWorkspaceDeleted}
      />,
    );
  }
  if (view === "performance" && courseManagerSession) {
    return deferred(<ProfessorCoursePerformance session={courseManagerSession} />);
  }
  if (view === "usage" && courseManagerSession) {
    return deferred(<ProfessorUsage session={courseManagerSession} />);
  }
  if (
    view === "performance" ||
    view === "usage" ||
    view === "course-management" ||
    view === "professor"
  ) {
    return (
      <CourseManagementAccessRequired
        label={
          view === "performance"
            ? "Course performance"
            : view === "usage"
              ? "Usage"
              : "Course management"
        }
        onBack={() => props.onViewChange(session ? "dashboard" : "login")}
      />
    );
  }
  if (view === "changelog") {
    return deferred(<ChangelogPage />);
  }
  if (view === "how-it-works" || view === "learning-science" || view === "privacy") {
    return deferred(<InfoPage kind={view} />);
  }
  if (!lesson.lecture) return <ViewLoadingState />;
  return deferred(
    <LessonWorkspace
      canvasDocument={lesson.canvasDocument}
      publishedCanvasView={lesson.publishedCanvasView}
      canvasError={lesson.canvasError}
      courseId={lesson.courseId}
      focusedSectionId={lesson.navigation.focusedSectionId}
      highlightedBlockId={lesson.navigation.highlightedBlockId}
      highlightedText={lesson.navigation.highlightedText}
      lecture={lesson.lecture}
      messages={lesson.messages}
      session={session ?? localDemoSession}
      tutorModel={lesson.lastTutorModel}
      navigationVersion={lesson.navigation.version}
      panelMode={lesson.panelMode}
      learnerState={lesson.lessonState.state}
      learnerStateError={lesson.lessonState.error}
      previewMode={lesson.mode === "professor-preview"}
      draftMode={lesson.mode === "draft"}
      workspaceMode={lesson.mode === "professor-preview" ? "professor-preview" : "learner"}
      onSendMessage={lesson.sendTutorMessage}
      onPracticeSubmitted={lesson.lessonState.applyQuizResult}
      onResetWorkspace={lesson.resetWorkspace}
      onTogglePanel={(mode) => {
        lesson.setPanelMode((current) => (current === mode ? null : mode));
      }}
    />,
  );
}

function deferred(content: ReactNode) {
  return <Suspense fallback={<ViewLoadingState />}>{content}</Suspense>;
}

function ViewLoadingState() {
  const { t } = useI18n();
  return (
    <main className="route-loading" aria-busy="true">
      <p role="status">{t("app.loadingView")}</p>
    </main>
  );
}
