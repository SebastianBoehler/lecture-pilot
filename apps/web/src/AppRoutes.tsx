import { CourseManagementAccessRequired } from "./CourseManagementAccessRequired";
import { Dashboard } from "./Dashboard";
import { draftPreviewUrl } from "./draftPreviewUrl";
import { LessonWorkspace } from "./LessonWorkspace";
import { LoginView } from "./LoginView";
import { InfoPage } from "./InfoPage";
import { localDemoSession } from "./appDefaults";
import { ProfileView } from "./ProfileView";
import { ProfessorCourseBuilder } from "./ProfessorCourseBuilder";
import { ProfessorCourseManagement } from "./ProfessorCourseManagement";
import { ProfessorCoursePerformance } from "./ProfessorCoursePerformance";
import { requestedTutorModel, type TutorModelPreference } from "./tutorModels";
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
  lessonUserId: string;
  messages: ChatMessage[];
  navigationVersion: number;
  panelMode: LessonPanelMode | null;
  publishedLectureIds: string[];
  selectedCourseId: string;
  selectedLecture: Lecture;
  session: LoginSession | null;
  tutorModelPreference: TutorModelPreference;
  view: View;
  workspaceCourse: UniversityCourse;
  workspaceCourseId: string;
  onLogin: (session: LoginSession) => void;
  onModelPreferenceChange: (model: TutorModelPreference) => void;
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
    lessonUserId,
    messages,
    navigationVersion,
    panelMode,
    publishedLectureIds,
    selectedCourseId,
    selectedLecture,
    session,
    tutorModelPreference,
    view,
    workspaceCourse,
    workspaceCourseId,
  } = props;

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
        modelPreference={tutorModelPreference}
        session={session}
        onBack={() => props.onViewChange("dashboard")}
        onModelPreferenceChange={props.onModelPreferenceChange}
      />
    );
  }
  if (view === "professor" && courseManagerSession) {
    return (
      <ProfessorCourseBuilder
        session={courseManagerSession}
        onPublishWorkspace={props.onPublishWorkspace}
        onWorkspacePublished={props.onWorkspacePublished}
        previewWorkspaceUrl={draftPreviewUrl}
        publishedLectureIds={publishedLectureIds}
      />
    );
  }
  if (view === "course-management" && courseManagerSession) {
    return (
      <ProfessorCourseManagement
        session={courseManagerSession}
        onWorkspaceDeleted={props.onWorkspaceDeleted}
      />
    );
  }
  if (view === "performance" && courseManagerSession) {
    return (
      <ProfessorCoursePerformance
        lectures={availableLectures}
        publishedLectureIds={publishedLectureIds}
        session={courseManagerSession}
        workspaceCourse={workspaceCourse}
      />
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
  if (view === "how-it-works" || view === "privacy") {
    return <InfoPage kind={view} onBack={() => props.onViewChange(session ? "dashboard" : "login")} />;
  }
  return (
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
      tutorModel={lastTutorModel ?? requestedTutorModel(tutorModelPreference)}
      navigationVersion={navigationVersion}
      panelMode={panelMode}
      userId={lessonUserId}
      backLabel={lessonBackView === "professor" ? "Course builder" : "Dashboard"}
      onBack={() => props.onViewChange(lessonBackView)}
      onSendMessage={props.onSendMessage}
      onResetWorkspace={props.onResetWorkspace}
      onTogglePanel={props.onTogglePanel}
    />
  );
}
