import { ChartNoAxesColumn, FilePlus2, LogOut, Moon, Sun, UserRound } from "lucide-react";

import { canManageCourses } from "./authz";
import type { LoginSession, Theme } from "./types";

export function AppHeader({
  session,
  theme,
  onBrand,
  onLogout,
  onOpenPerformance,
  onOpenProfile,
  onOpenProfessor,
  onToggleTheme,
}: {
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
  return (
    <header className="top-bar">
      <button className="brand" type="button" onClick={onBrand}>
        <span>LecturePilot</span>
      </button>
      <div className="top-status">
        <span>Course workspace</span>
        {session ? (
          <div className="top-actions" aria-label="Account controls">
            {canManageCourses(session) ? (
              <>
                <button className="top-action-button" type="button" onClick={onOpenPerformance}>
                  <ChartNoAxesColumn size={16} />
                  <span>Course performance</span>
                </button>
                <button className="top-action-button" type="button" onClick={onOpenProfessor}>
                  <FilePlus2 size={16} />
                  <span>Course builder</span>
                </button>
              </>
            ) : null}
            <button className="top-action-button" type="button" aria-label="Open profile" onClick={onOpenProfile}>
              <UserRound size={16} />
              <span>Profile</span>
            </button>
            <button className="top-action-button" type="button" aria-label="Log out" onClick={onLogout}>
              <LogOut size={16} />
              <span>Log out</span>
            </button>
          </div>
        ) : null}
        <button className="icon-button" type="button" aria-label={`Switch to ${nextTheme} mode`} onClick={onToggleTheme}>
          {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
        </button>
      </div>
    </header>
  );
}
