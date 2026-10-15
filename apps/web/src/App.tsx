import { lazy, Suspense, useCallback, useEffect, useEffectEvent, useState } from "react";

import { publishLectureCanvas } from "./shared/api";
import { AppFooter } from "./shell/AppFooter";
import { AppHeader } from "./shell/AppHeader";
import { landingView, resolveLandingView } from "./shell/appLanding";
import { AppRoutes } from "./AppRoutes";
import { pathForView, readAppRoute, requiresSession } from "./shell/appRoute";
import { FeedbackDialog } from "./shell/FeedbackDialog";
import { localDemoSession, localProfessorSession } from "./shell/appDefaults";
import { canManageCourses } from "./shared/authz";
import { clearDemoWorkspaceCourse } from "./auth/demoWorkspaceAccess";
import { I18nProvider, type Locale } from "./i18n/i18n";
import { readLocalePreference, writeLocalePreference } from "./i18n/localePreference";
import { clearSavedFlow } from "./professor/professorBuilderState";
import { rememberReturnPath, takeReturnPath } from "./shell/returnPath";
import { SessionExpiredNotice } from "./auth/SessionExpiredNotice";
import { useStoredLoginSession } from "./auth/loginSessionStorage";
import { readAccountLink } from "./auth/accountActions";
import { logoutSession } from "./auth/sessionApi";
import { clearAllPracticeExamDrafts } from "./exam/practiceExamDraft";
import { usePublicMetadata } from "./info/usePublicMetadata";
import { useAppRoute } from "./shell/useAppRoute";
import { useCourseWorkspace } from "./dashboard/useCourseWorkspace";
import { useLessonSession } from "./lesson/useLessonSession";
import { useUniversityCourseSync } from "./professor/useUniversityCourseSync";
import { useFeedbackPrompt } from "./shell/useFeedbackPrompt";
import { useViewTransitionReset } from "./shell/useViewTransitionReset";
import { useVersionUpdateActivity } from "./shell/VersionUpdateBoundary";
import type { LoginSession, Theme, View } from "./shared/types";

// The guided tour (and its positioning library) only ever loads for course managers.
const ProfessorWalkthrough = lazy(() =>
  import("./professor/ProfessorWalkthrough").then((module) => ({
    default: module.ProfessorWalkthrough,
  })),
);

type ManagedView = "performance" | "usage" | "course-management" | "professor";

function App() {
  const [theme, setTheme] = useState<Theme>("light");
  const [locale, setLocale] = useState<Locale>(() => readLocalePreference());
  const { navigate, route } = useAppRoute();
  const [session, setSession, restoringSession, sessionExpired] = useStoredLoginSession();
  const [accountLinkActive, setAccountLinkActive] = useState(
    () => readAccountLink().mode !== "login",
  );
  const view =
    accountLinkActive || (!session && requiresSession(route.view)) ? "login" : route.view;
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
    if (!session || route.view !== "login" || accountLinkActive) return;
    const returnPath = takeReturnPath();
    const landing = landingView(session);
    // Course managers' landing depends on whether they already have courses.
    if (!returnPath && landing === "professor") {
      void openLandingAfterLogin(session);
      return;
    }
    navigate(returnPath ?? pathForView(landing), { replace: true });
    setPanelMode(null);
  }, [accountLinkActive, navigate, route.view, session, setPanelMode]);

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
          onOpenCourseDemand={() => changeView("course-demand")}
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
          accountLinkActive={accountLinkActive}
          route={route}
          session={session}
          view={view}
          onLogout={handleLogout}
          // The login effect then continues to a remembered return path (e.g. a shared
          // course link) or the account's landing view.
          onLogin={(nextSession) => {
            setAccountLinkActive(false);
            setSession(nextSession);
          }}
          onOpenDemo={() => {
            setAccountLinkActive(false);
            setSession(localDemoSession);
          }}
          onOpenCourseLink={openCourseLink}
          onOpenProfessorDemo={() => {
            setAccountLinkActive(false);
            setSession(localProfessorSession);
          }}
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
