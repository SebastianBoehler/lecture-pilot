import { ChartNoAxesColumn, FilePlus2, LogOut, Moon, Sun, UserRound } from "lucide-react";

import { canManageCourses } from "./authz";
import type { LoginSession, Theme, View } from "./types";

export function AppHeader({
  activeView,
  session,
  theme,
  onBrand,
  onLogout,
  onOpenPerformance,
  onOpenProfile,
  onOpenProfessor,
  onToggleTheme,
}: {
  activeView: View;
  session: LoginSession | null;
  theme: Theme;
  onBrand: () => void;
  onLogout: () => void;
  onOpenPerformance: () => void;
  onOpenProfile: () => void;
  onOpenProfessor: () => void;
  onToggleTheme: () => void;
}) {
  const nextTheme = theme === "light" ? "dark" : "light";
  const canManage = canManageCourses(session);
  return (
    <header className="top-bar">
      <div className="top-brand-zone">
        <button className="brand" type="button" onClick={onBrand}>
          <span>LecturePilot</span>
        </button>
      </div>
      {canManage ? (
        <nav className="top-primary-nav" aria-label="Professor workspace navigation">
          <button
            className={`top-nav-button ${activeView === "performance" ? "is-active" : ""}`}
            type="button"
            onClick={onOpenPerformance}
          >
            <ChartNoAxesColumn size={16} />
            <span>Course performance</span>
          </button>
          <button
            className={`top-nav-button ${activeView === "professor" ? "is-active" : ""}`}
            type="button"
            onClick={onOpenProfessor}
          >
            <FilePlus2 size={16} />
            <span>Course builder</span>
          </button>
        </nav>
      ) : (
        <div />
      )}
      <div className="top-utility-actions" aria-label="Account controls">
        {session ? (
          <>
            <button className="top-icon-button" type="button" aria-label="Open profile" onClick={onOpenProfile}>
              <UserRound size={17} />
            </button>
            <button className="top-icon-button" type="button" aria-label="Log out" onClick={onLogout}>
              <LogOut size={17} />
            </button>
          </>
        ) : null}
        <button className="top-icon-button" type="button" aria-label={`Switch to ${nextTheme} mode`} onClick={onToggleTheme}>
          {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
        </button>
      </div>
    </header>
  );
}
