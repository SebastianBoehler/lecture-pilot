import { useI18n } from "./i18n";
import type { LoginSession } from "./types";
import { UniversityLoginForm } from "./UniversityLoginForm";

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

  return (
    <main className="login-screen">
      <section className="login-panel" aria-labelledby="login-heading">
        <div className="login-copy">
          <h1 id="login-heading">{t("login.title")}</h1>
          <p>{t("login.subtitle")}</p>
        </div>
        <div className="login-auth-panel">
          <UniversityLoginForm
            onLogin={onLogin}
            onOpenDemo={onOpenDemo}
            onOpenProfessorDemo={onOpenProfessorDemo}
            showDemoAccess={showDemoAccess}
          />
        </div>
      </section>
    </main>
  );
}
