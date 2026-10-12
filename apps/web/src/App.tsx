import { lazy, Suspense, useCallback, useEffect, useEffectEvent, useState } from "react";

import { publishLectureCanvas } from "./api";
import { AppFooter } from "./AppFooter";
import { AppHeader } from "./AppHeader";
import { landingView, resolveLandingView } from "./appLanding";
import { AppRoutes } from "./AppRoutes";
import { pathForView, readAppRoute, requiresSession } from "./appRoute";
import { FeedbackDialog } from "./FeedbackDialog";
import { localDemoSession, localProfessorSession } from "./appDefaults";
import { canManageCourses } from "./authz";
import { clearDemoWorkspaceCourse } from "./demoWorkspaceAccess";
import { I18nProvider, type Locale } from "./i18n";
import { readLocalePreference, writeLocalePreference } from "./localePreference";
import { clearSavedFlow } from "./professorBuilderState";
import { rememberReturnPath, takeReturnPath } from "./returnPath";
import { SessionExpiredNotice } from "./SessionExpiredNotice";
import { useStoredLoginSession } from "./loginSessionStorage";
import { logoutSession } from "./sessionApi";
import { clearAllPracticeExamDrafts } from "./practiceExamDraft";
import { usePublicMetadata } from "./usePublicMetadata";
import { useAppRoute } from "./useAppRoute";
import { useCourseWorkspace } from "./useCourseWorkspace";
import { useLessonSession } from "./useLessonSession";
import { useUniversityCourseSync } from "./useUniversityCourseSync";
import { useFeedbackPrompt } from "./useFeedbackPrompt";
import { useViewTransitionReset } from "./useViewTransitionReset";
import { useVersionUpdateActivity } from "./VersionUpdateBoundary";
import type { LoginSession, Theme, View } from "./types";

// The guided tour (and its positioning library) only ever loads for course managers.
const ProfessorWalkthrough = lazy(() =>
  import("./ProfessorWalkthrough").then((module) => ({ default: module.ProfessorWalkthrough })),
);

type ManagedView = "performance" | "usage" | "course-management" | "professor";

function App() {
  const [theme, setTheme] = useState<Theme>("light");
  const [locale, setLocale] = useState<Locale>(() => readLocalePreference());
  const { navigate, route } = useAppRoute();
  const [session, setSession, restoringSession, sessionExpired] = useStoredLoginSession();
  const view = !session && requiresSession(route.view) ? "login" : route.view;
  usePublicMetadata(view, locale);
  const feedback = useFeedbackPrompt(session, view === "dashboard");
  const workspace = useCourseWorkspace(route, session, setSession);
  const lesson = useLessonSession({
    route,
    session,
    enabled: view === "lesson",
    locale,
    navigate,
    workspace,
    onTutorTurn: feedback.recordSuccessfulTutorTurn,
  });
  const { setPanelMode } = lesson;
  useVersionUpdateActivity(lesson.messages.some((message) => Boolean(message.isPending)));
  useUniversityCourseSync(session, setSession);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = locale;
    writeLocalePreference(locale);
  }, [locale]);

  async function openLanding(activeSession: LoginSession, afterLogin: boolean) {
    const landing = await resolveLandingView(activeSession);
    // A visitor who already moved on while the landing resolved keeps their choice.
    if (afterLogin && readAppRoute(window.location).view !== "login") return;
    navigate(pathForView(landing), { replace: afterLogin });
    setPanelMode(null);
  }
  const openLandingAfterLogin = useEffectEvent((activeSession: LoginSession) =>
    openLanding(activeSession, true),
  );

  useEffect(() => {
    if (!session || route.view !== "login") return;
    const returnPath = takeReturnPath();
    const landing = landingView(session);
    // Course managers' landing depends on whether they already have courses.
    if (!returnPath && landing === "professor") {
      void openLandingAfterLogin(session);
      return;
    }
    navigate(returnPath ?? pathForView(landing), { replace: true });
    setPanelMode(null);
  }, [navigate, route.view, session, setPanelMode]);

  useEffect(() => {
    if (!restoringSession && !session && requiresSession(route.view)) {
      navigate(pathForView("login"), { replace: true });
    }
  }, [navigate, restoringSession, route.view, session]);

  useViewTransitionReset(view);

  async function loadWorkspaceCourse(activeSession: LoginSession, preferredCourseId: string) {
    const loaded = await workspace.load(activeSession, preferredCourseId);
    if (loaded) lesson.selectCourse(loaded.course.id, loaded.lectures);
  }

  const loadWorkspaceCourseFromSession = useEffectEvent((activeSession: LoginSession) =>
    loadWorkspaceCourse(activeSession, workspace.courseId),
  );
  const shouldLoadWorkspaceFromSession = route.view !== "lesson";

  useEffect(() => {
    if (
      !session ||
      session.university_course_sync_status === "loading" ||
      !shouldLoadWorkspaceFromSession
    )
      return;
    void loadWorkspaceCourseFromSession(session);
  }, [session, shouldLoadWorkspaceFromSession]);

  function handleLogout() {
    if (session) void logoutSession(session);
    setSession(null);
    clearSavedFlow();
    clearAllPracticeExamDrafts();
    takeReturnPath(); // An explicit logout ends the previous user's pending destination.
    navigate(pathForView("login"), { replace: true });
    lesson.clear();
    workspace.clearLoadError();
  }

  function handleWorkspaceDeleted(courseId: string) {
    clearDemoWorkspaceCourse(courseId);
    clearSavedFlow();
    workspace.clearPublished();
    if (workspace.courseId === courseId || lesson.courseId === courseId) {
      void loadWorkspaceCourse(
        session ?? localDemoSession,
        import.meta.env.DEV ? localDemoSession.courses[0].id : "",
      );
    }
  }

  const courseManagerSession = canManageCourses(session) ? session : null;
  const openCourseLink = useCallback(
    (courseId: string) => {
      if (!session) return;
      void loadWorkspaceCourse(session, courseId).then(() =>
        navigate(pathForView("dashboard"), { replace: true }),
      );
    },
    // loadWorkspaceCourse only reads current state setters and the given session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [navigate, session],
  );

  function changeView(nextView: View, replace = false) {
    if (nextView === "lesson" || nextView === "course-link") return;
    navigate(pathForView(nextView), { replace });
    setPanelMode(null);
  }

  function openManagedView(nextView: ManagedView) {
    if (courseManagerSession) changeView(nextView);
  }

  return (
    <I18nProvider locale={locale} setLocale={setLocale}>
      <div className="app-shell">
        {sessionExpired ? (
          <SessionExpiredNotice
            onSignIn={() => {
              rememberReturnPath(window.location.pathname);
              setSession(null);
              navigate(pathForView("login"), { replace: true });
            }}
          />
        ) : null}
        <AppHeader
          activeView={view}
          session={session}
          theme={theme}
          onBrand={() => {
            if (session) void openLanding(session, false);
            else changeView("login");
          }}
          onOpenDashboard={() => changeView(session ? "dashboard" : "login")}
          onOpenPerformance={() => openManagedView("performance")}
          onOpenUsage={() => openManagedView("usage")}
          onOpenCourseManagement={() => openManagedView("course-management")}
          onOpenProfile={() => changeView("profile")}
          onOpenProfessor={() => openManagedView("professor")}
          onOpenFeedback={feedback.openManually}
          onToggleTheme={() => setTheme(theme === "light" ? "dark" : "light")}
        />
        {session && feedback.source ? (
          <FeedbackDialog
            accountType={session.account_type ?? "student"}
            context={
              view === "lesson" && lesson.lecture
                ? { courseTitle: workspace.course.title, lectureTitle: lesson.lecture.title }
                : {}
            }
            key={feedback.source}
            source={feedback.source}
            onClose={feedback.close}
          />
        ) : null}
        {courseManagerSession && view !== "lesson" ? (
          <Suspense fallback={null}>
            <ProfessorWalkthrough
              key={courseManagerSession.username}
              onViewChange={(nextView) => changeView(nextView)}
              username={courseManagerSession.username}
            />
          </Suspense>
        ) : null}

        <AppRoutes
          workspace={workspace}
          lesson={lesson}
          courseManagerSession={courseManagerSession}
          restoringSession={restoringSession}
          route={route}
          session={session}
          view={view}
          onLogout={handleLogout}
          // The login effect then continues to a remembered return path (e.g. a shared
          // course link) or the account's landing view.
          onLogin={setSession}
          onOpenDemo={() => setSession(localDemoSession)}
          onOpenCourseLink={openCourseLink}
          onOpenProfessorDemo={() => setSession(localProfessorSession)}
          onNavigatePath={navigate}
          onSetAttendance={(lectureId, attendance) => {
            workspace.setAttendance(lectureId, attendance);
            lesson.setAttendance(lectureId, attendance);
          }}
          onPublishWorkspace={async (courseId, lectureId, approval) => {
            if (!courseManagerSession)
              throw new Error("Course management requires a professor account.");
            const result = await publishLectureCanvas(
              courseId,
              lectureId,
              courseManagerSession,
              approval,
            );
            workspace.markPublished(lectureId);
            return result;
          }}
          onWorkspacePublished={(course, nextLectures) => {
            if (!nextLectures.length) return;
            lesson.selectCourse(course.id, workspace.showPublished(course, nextLectures));
          }}
          onWorkspaceDeleted={handleWorkspaceDeleted}
          onViewChange={changeView}
        />
        {!restoringSession && view !== "lesson" ? (
          <AppFooter
            onOpenChangelog={() => changeView("changelog")}
            onOpenHowItWorks={() => changeView("how-it-works")}
            onOpenLearningScience={() => changeView("learning-science")}
            onOpenPrivacy={() => changeView("privacy")}
          />
        ) : null}
      </div>
    </I18nProvider>
  );
}

export default App;
