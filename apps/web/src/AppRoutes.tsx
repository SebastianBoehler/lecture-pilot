import type { LearningDesignApprovalInput } from "./professor/learningDesignTypes";
import { CourseLinkView } from "./professor/CourseLinkView";
import { rememberReturnPath } from "./shell/returnPath";
import { clearSavedFlow, writeResumeFlow } from "./professor/professorBuilderState";
import { lazy, Suspense, type ReactNode } from "react";

import { coursePagePath, type AppRoute } from "./shell/appRoute";
import { CourseManagementAccessRequired } from "./professor/CourseManagementAccessRequired";
import { PlatformAdminRequired } from "./admin/PlatformAdminRequired";
import { isPlatformAdmin } from "./shared/authz";
import { Dashboard } from "./dashboard/Dashboard";
import { draftPreviewUrl } from "./lesson/draftPreviewUrl";
import { LoginView } from "./auth/LoginView";
import { localDemoSession } from "./shell/appDefaults";
import { ProfileView } from "./profile/ProfileView";
import { useI18n } from "./i18n/i18n";
import type { CourseWorkspace } from "./dashboard/useCourseWorkspace";
import { useLearnerProfile } from "./profile/useLearnerProfile";
import type { LessonSession } from "./lesson/useLessonSession";
import type {
  Attendance,
  CanvasPublicationResult,
  Lecture,
  LoginSession,
  UniversityCourse,
  View,
} from "./shared/types";

const InfoPage = lazy(() =>
  import("./info/InfoPage").then((module) => ({ default: module.InfoPage })),
);
const ChangelogPage = lazy(() =>
  import("./info/ChangelogPage").then((module) => ({ default: module.ChangelogPage })),
);
const LessonWorkspace = lazy(() =>
  import("./lesson/LessonWorkspace").then((module) => ({ default: module.LessonWorkspace })),
);
const ProfessorCourseBuilder = lazy(() =>
  import("./professor/ProfessorCourseBuilder").then((module) => ({
    default: module.ProfessorCourseBuilder,
  })),
);
const ProfessorCourseManagement = lazy(() =>
  import("./professor/ProfessorCourseManagement").then((module) => ({
    default: module.ProfessorCourseManagement,
  })),
);
const ProfessorCoursePerformance = lazy(() =>
  import("./performance/ProfessorPerformanceDashboard").then((module) => ({
    default: module.ProfessorPerformanceDashboard,
  })),
);
const CourseDemandPage = lazy(() =>
  import("./admin/CourseDemandPage").then((module) => ({ default: module.CourseDemandPage })),
);
const ProfessorUsage = lazy(() =>
  import("./performance/ProfessorUsage").then((module) => ({ default: module.ProfessorUsage })),
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
  onPublishWorkspace: (
    courseId: string,
    lectureId: string,
    approval: LearningDesignApprovalInput,
  ) => Promise<CanvasPublicationResult>;
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
        onOpen={(courseId, lecture, review, focusSectionId) => {
          void lesson.openLecture(courseId, lecture, "learner", true, review, focusSectionId);
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
        onCloseCourse={() => props.onViewChange("course-management")}
        onPreviewLecture={(courseId, lecture) => {
          void lesson.openLecture(courseId, lecture, "professor-preview");
        }}
        onOpenCourse={(courseId) => props.onNavigatePath(coursePagePath(courseId))}
        session={courseManagerSession}
        courseId={route.view === "course-management" ? route.courseId : undefined}
        onWorkspaceDeleted={props.onWorkspaceDeleted}
      />,
    );
  }
  if (view === "performance" && courseManagerSession) {
    return deferred(<ProfessorCoursePerformance session={courseManagerSession} />);
  }
  if (view === "course-demand") {
    return session && isPlatformAdmin(session) ? (
      deferred(<CourseDemandPage session={session} />)
    ) : (
      <PlatformAdminRequired onBack={() => props.onViewChange(session ? "dashboard" : "login")} />
    );
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
