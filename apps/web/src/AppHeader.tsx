import {
  ChartNoAxesColumn,
  FilePlus2,
  FolderOpen,
  Gauge,
  Home,
  Languages,
  LogOut,
  Moon,
  Sun,
  UserRound,
} from "lucide-react";

import { canManageCourses, isStudentAccount } from "./authz";
import { useI18n } from "./i18n";
import type { LoginSession, Theme, View } from "./types";

export function AppHeader({
  activeView,
  session,
  theme,
  onBrand,
  onLogout,
  onOpenDashboard,
  onOpenCourseManagement,
  onOpenPerformance,
  onOpenUsage,
  onOpenProfile,
  onOpenProfessor,
  onToggleTheme,
}: {
  activeView: View;
  session: LoginSession | null;
  theme: Theme;
  onBrand: () => void;
  onLogout: () => void;
  onOpenDashboard: () => void;
  onOpenCourseManagement: () => void;
  onOpenPerformance: () => void;
  onOpenUsage: () => void;
  onOpenProfile: () => void;
  onOpenProfessor: () => void;
  onToggleTheme: () => void;
}) {
  const { locale, setLocale, t } = useI18n();
  const nextTheme = theme === "light" ? "dark" : "light";
  const nextThemeLabel = nextTheme === "light" ? t("app.theme.light") : t("app.theme.dark");
  const nextLocale = locale === "en" ? "de" : "en";
  const canManage = canManageCourses(session);
  return (
    <header className="top-bar">
      <div className="top-brand-zone">
        <button className="brand" type="button" onClick={onBrand}>
          <span>LecturePilot</span>
        </button>
      </div>
      {canManage ? (
        <nav className="top-primary-nav" aria-label={t("nav.professor")}>
          <button
            className={`top-nav-button ${activeView === "performance" ? "is-active" : ""}`}
            type="button"
            onClick={onOpenPerformance}
          >
            <ChartNoAxesColumn size={16} />
            <span>{t("nav.performance")}</span>
          </button>
          <button
            className={`top-nav-button ${activeView === "usage" ? "is-active" : ""}`}
            type="button"
            onClick={onOpenUsage}
          >
            <Gauge size={16} />
            <span>{t("nav.usage")}</span>
          </button>
          <button
            className={`top-nav-button ${activeView === "course-management" ? "is-active" : ""}`}
            type="button"
            onClick={onOpenCourseManagement}
          >
            <FolderOpen size={16} />
            <span>{t("nav.manageCourses")}</span>
          </button>
          <button
            className={`top-nav-button ${activeView === "professor" ? "is-active" : ""}`}
            type="button"
            onClick={onOpenProfessor}
          >
            <FilePlus2 size={16} />
            <span>{t("nav.courseBuilder")}</span>
          </button>
        </nav>
      ) : isStudentAccount(session) ? (
        <nav className="top-primary-nav" aria-label={t("nav.student")}>
          <button
            className={`top-nav-button ${activeView === "dashboard" ? "is-active" : ""}`}
            type="button"
            onClick={onOpenDashboard}
          >
            <Home size={16} />
            <span>{t("nav.workspaces")}</span>
          </button>
        </nav>
      ) : (
        <div />
      )}
      <div className="top-utility-actions" aria-label={t("nav.accountControls")}>
        {session ? (
          <>
            <button
              className="top-icon-button"
              type="button"
              aria-label={t("nav.openProfile")}
              onClick={onOpenProfile}
            >
              <UserRound size={17} />
            </button>
            <button
              className="top-icon-button"
              type="button"
              aria-label={t("nav.logout")}
              onClick={onLogout}
            >
              <LogOut size={17} />
            </button>
          </>
        ) : null}
        <button
          className="top-icon-button language-toggle"
          type="button"
          aria-label={locale === "en" ? t("app.switchToGerman") : t("app.switchToEnglish")}
          onClick={() => setLocale(nextLocale)}
        >
          <Languages size={14} />
          <span aria-hidden="true">{nextLocale.toUpperCase()}</span>
        </button>
        <button
          className="top-icon-button"
          type="button"
          aria-label={t("app.theme.switch", { theme: nextThemeLabel })}
          onClick={onToggleTheme}
        >
          {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
        </button>
      </div>
    </header>
  );
}
