import { useState } from "react";

import { useI18n } from "./i18n";
import { ProfessorAuthForm } from "./ProfessorAuthForm";
import { StudentLoginForm } from "./StudentLoginForm";
import type { LoginSession } from "./types";

type LoginAudience = "student" | "professor";

export function LoginView({
  onLogin,
  onOpenDemo,
  onOpenProfessorDemo,
  showDemoAccess = import.meta.env.DEV,
}: {
  onLogin: (session: LoginSession) => void;
  onOpenDemo: () => void;
  onOpenProfessorDemo: () => void;
  showDemoAccess?: boolean;
}) {
  const { t } = useI18n();
  const [audience, setAudience] = useState<LoginAudience>("student");

  return (
    <main className="login-screen">
      <section className="login-panel" aria-labelledby="login-heading">
        <div className="login-copy">
          <h1 id="login-heading">{t("login.title")}</h1>
          <p>{t("login.subtitle")}</p>
        </div>
        <div className="login-auth-panel">
          <div className="login-role-tabs" role="tablist" aria-label={t("login.accountType")}>
            <button
              aria-selected={audience === "student"}
              className={audience === "student" ? "is-active" : ""}
              role="tab"
              type="button"
              onClick={() => setAudience("student")}
            >
              {t("login.studentTab")}
            </button>
            <button
              aria-selected={audience === "professor"}
              className={audience === "professor" ? "is-active" : ""}
              role="tab"
              type="button"
              onClick={() => setAudience("professor")}
            >
              {t("login.professorTab")}
            </button>
          </div>
          {audience === "student" ? (
            <StudentLoginForm
              onLogin={onLogin}
              onOpenDemo={onOpenDemo}
              onOpenProfessorDemo={onOpenProfessorDemo}
              showDemoAccess={showDemoAccess}
            />
          ) : (
            <ProfessorAuthForm onLogin={onLogin} />
          )}
        </div>
      </section>
    </main>
  );
}
