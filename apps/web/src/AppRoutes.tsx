import { lazy, Suspense, type ReactNode } from "react";

import { CourseManagementAccessRequired } from "./CourseManagementAccessRequired";
import { Dashboard } from "./Dashboard";
import { draftPreviewUrl } from "./draftPreviewUrl";
import { LoginView } from "./LoginView";
import { localDemoSession } from "./appDefaults";
import { ProfileView } from "./ProfileView";
import { useI18n } from "./i18n";
import { useLearnerProfile } from "./useLearnerProfile";
import type { WorkspaceResetSelection } from "./WorkspaceResetControl";
import type {
  Attendance,
  CanvasDocument,
  CanvasPublicationResult,
  ChatMessage,
  LessonPanelMode,
  Lecture,
  LoginSession,
  UniversityCourse,
  View,
} from "./types";

const InfoPage = lazy(() => import("./InfoPage").then((module) => ({ default: module.InfoPage })));
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
  import("./ProfessorCoursePerformance").then((module) => ({
    default: module.ProfessorCoursePerformance,
  })),
);

type AppRoutesProps = {
  availableLectures: Lecture[];
  canvasDocument: CanvasDocument | null;
  canvasError: string | null;
  courseManagerSession: LoginSession | null;
  focusedSectionId: string;
  highlightedBlockId: string | null;
  highlightedText: string | null;
  lastTutorModel: string | null;
  lessonBackView: "dashboard" | "professor";
  messages: ChatMessage[];
  navigationVersion: number;
  panelMode: LessonPanelMode | null;
  passedGateIds: string[];
  publishedLectureIds: string[];
  selectedCourseId: string;
  selectedLecture: Lecture;
  session: LoginSession | null;
  view: View;
  workspaceCourse: UniversityCourse;
  workspaceCourseId: string;
  onLogin: (session: LoginSession) => void;
  onSessionChange: (session: LoginSession) => void;
  onOpenDemo: () => void;
  onOpenLecture: (courseId: string, lecture: Lecture) => void;
  onOpenProfessorDemo: () => void;
  onPublishWorkspace: (courseId: string, lectureId: string) => Promise<CanvasPublicationResult>;
  onResetWorkspace: (options: WorkspaceResetSelection) => Promise<void>;
  onSendMessage: (message: string) => Promise<void>;
  onSetAttendance: (lectureId: string, attendance: Attendance) => void;
  onTogglePanel: (mode: LessonPanelMode) => void;
  onViewChange: (view: View) => void;
  onWorkspaceDeleted: (courseId: string) => void;
  onWorkspacePublished: (course: UniversityCourse, lectures: Lecture[]) => void;
};

export function AppRoutes(props: AppRoutesProps) {
  const {
    availableLectures,
    canvasDocument,
    canvasError,
    courseManagerSession,
    focusedSectionId,
    highlightedBlockId,
    highlightedText,
    lastTutorModel,
    lessonBackView,
    messages,
    navigationVersion,
    panelMode,
    publishedLectureIds,
    selectedCourseId,
    selectedLecture,
    session,
    view,
    workspaceCourse,
    workspaceCourseId,
  } = props;
  const learnerProfileEnabled = Boolean(
    session &&
    (session.account_type ?? "student") === "student" &&
    !session.roles?.includes("tenant_admin"),
  );
  const learnerProfileState = useLearnerProfile(session, learnerProfileEnabled);

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
        lectures={availableLectures}
        publishedLectureIds={publishedLectureIds}
        learnerProfileState={learnerProfileState}
        session={session}
        workspaceCourse={workspaceCourse}
        onOpen={(lecture) => props.onOpenLecture(workspaceCourseId, lecture)}
        onSetAttendance={props.onSetAttendance}
      />
    );
  }
  if (view === "profile" && session) {
    return (
      <ProfileView
        learnerProfileState={learnerProfileState}
        session={session}
        onBack={
          session.account_type === "professor" && !courseManagerSession
            ? undefined
            : () => props.onViewChange(courseManagerSession ? "professor" : "dashboard")
        }
        onSessionChange={props.onSessionChange}
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
        publishedLectureIds={publishedLectureIds}
      />,
    );
  }
  if (view === "course-management" && courseManagerSession) {
    return deferred(
      <ProfessorCourseManagement
        onCreateCourse={() => props.onViewChange("professor")}
        session={courseManagerSession}
        onWorkspaceDeleted={props.onWorkspaceDeleted}
      />,
    );
  }
  if (view === "performance" && courseManagerSession) {
    return deferred(
      <ProfessorCoursePerformance
        lectures={availableLectures}
        publishedLectureIds={publishedLectureIds}
        session={courseManagerSession}
        workspaceCourse={workspaceCourse}
      />,
    );
  }
  if (view === "performance" || view === "course-management" || view === "professor") {
    return (
      <CourseManagementAccessRequired
        label={view === "performance" ? "Course performance" : "Course management"}
        onBack={() => props.onViewChange(session ? "dashboard" : "login")}
      />
    );
  }
  if (view === "how-it-works" || view === "learning-science" || view === "privacy") {
    return deferred(
      <InfoPage kind={view} onBack={() => props.onViewChange(session ? "dashboard" : "login")} />,
    );
  }
  return deferred(
    <LessonWorkspace
      canvasDocument={canvasDocument}
      canvasError={canvasError}
      courseId={selectedCourseId}
      focusedSectionId={focusedSectionId}
      highlightedBlockId={highlightedBlockId}
      highlightedText={highlightedText}
      lecture={selectedLecture}
      messages={messages}
      session={session ?? localDemoSession}
      tutorModel={lastTutorModel}
      navigationVersion={navigationVersion}
      panelMode={panelMode}
      passedGateIds={props.passedGateIds}
      backLabel={lessonBackView === "professor" ? "Course builder" : "Dashboard"}
      onBack={() => props.onViewChange(lessonBackView)}
      onSendMessage={props.onSendMessage}
      onResetWorkspace={props.onResetWorkspace}
      onTogglePanel={props.onTogglePanel}
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
