import { FormEvent, useState } from "react";

import { useI18n } from "./i18n";
import { loginWithTuebingen } from "./sessionApi";
import type { LoginSession } from "./types";

export function LoginView({
  onLogin,
  onOpenDemo,
  onOpenProfessorDemo,
}: {
  onLogin: (session: LoginSession) => void;
  onOpenDemo: () => void;
  onOpenProfessorDemo: () => void;
}) {
  const { t } = useI18n();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username.trim() || !password || isSubmitting) {
      return;
    }

    setError(null);
    setIsSubmitting(true);
    try {
      const session = await loginWithTuebingen({
        username: username.trim(),
        password,
      });
      onLogin(session);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : t("login.failed"));
    } finally {
      setPassword("");
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-screen">
      <section className="login-panel" aria-labelledby="login-heading">
        <div className="login-copy">
          <h1 id="login-heading">{t("login.title")}</h1>
          <p>{t("login.subtitle")}</p>
        </div>

        <form className="login-form" onSubmit={submitLogin}>
          <label>
            {t("login.username")}
            <input
              autoComplete="username"
              name="username"
              onChange={(event) => setUsername(event.target.value)}
              value={username}
            />
          </label>
          <label>
            {t("login.password")}
            <input
              autoComplete="current-password"
              name="password"
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              value={password}
            />
          </label>
          <button
            className="login-submit-button"
            disabled={isSubmitting || !username.trim() || !password}
            type="submit"
          >
            {isSubmitting ? <span className="login-spinner" aria-hidden="true" /> : null}
            {isSubmitting ? t("login.submitting") : t("login.submit")}
          </button>
          {isSubmitting ? (
            <p className="login-status" role="status">
              {t("login.status")}
            </p>
          ) : null}
          <button
            className="secondary-button"
            disabled={isSubmitting}
            type="button"
            onClick={onOpenDemo}
          >
            {t("login.demo")}
          </button>
          <button
            className="secondary-button"
            disabled={isSubmitting}
            type="button"
            onClick={onOpenProfessorDemo}
          >
            {t("login.professorDemo")}
          </button>
          {error ? <p className="form-error">{error}</p> : null}
        </form>
      </section>
    </main>
  );
}
