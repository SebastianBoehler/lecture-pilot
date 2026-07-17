import { FormEvent, useState } from "react";

import { useI18n } from "./i18n";
import { useRememberedLoginIdentifier } from "./loginPreferences";
import { loginWithTuebingen } from "./sessionApi";
import type { LoginSession } from "./types";
import { useVersionUpdateActivity } from "./VersionUpdateBoundary";

export function UniversityLoginForm({
  onLogin,
  onOpenDemo,
  onOpenProfessorDemo,
  showDemoAccess,
}: {
  onLogin: (session: LoginSession) => void;
  onOpenDemo: () => void;
  onOpenProfessorDemo: () => void;
  showDemoAccess: boolean;
}) {
  const { t } = useI18n();
  const {
    identifier: username,
    persistRememberedIdentifier,
    remember: rememberUsername,
    setIdentifier: setUsername,
    setRemember: setRememberUsername,
  } = useRememberedLoginIdentifier();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [initialUsername] = useState(username);
  useVersionUpdateActivity(isSubmitting || Boolean(password) || username !== initialUsername);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username.trim() || !password || isSubmitting) return;
    setError(null);
    setIsSubmitting(true);
    try {
      const session = await loginWithTuebingen({
        username: username.trim(),
        password,
      });
      persistRememberedIdentifier();
      onLogin(session);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : t("login.failed"));
    } finally {
      setPassword("");
      setIsSubmitting(false);
    }
  }

  return (
    <form autoComplete="on" className="login-form" method="post" onSubmit={submitLogin}>
      <label>
        {t("login.username")}
        <input
          autoCapitalize="none"
          autoComplete="username"
          id="username"
          maxLength={120}
          name="username"
          onChange={(event) => setUsername(event.target.value)}
          required
          spellCheck={false}
          value={username}
        />
      </label>
      <label>
        {t("login.password")}
        <input
          autoComplete="current-password"
          id="university-current-password"
          maxLength={500}
          name="password"
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
      </label>
      <div className="login-checkbox">
        <input
          aria-describedby="university-remember-help"
          checked={rememberUsername}
          id="remember-username"
          name="remember_username"
          onChange={(event) => setRememberUsername(event.target.checked)}
          type="checkbox"
        />
        <span className="login-remember-copy">
          <label className="login-remember-label" htmlFor="remember-username">
            {t("login.rememberUsername")}
          </label>
          <span className="login-help" id="university-remember-help">
            {t("login.rememberHelp")}
          </span>
        </span>
      </div>
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
      {showDemoAccess ? (
        <section className="login-demo-actions" aria-labelledby="login-demo-title">
          <div className="login-demo-copy">
            <h2 id="login-demo-title">{t("login.demoTitle")}</h2>
            <p>{t("login.demoHelp")}</p>
          </div>
          <div className="login-demo-buttons">
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
          </div>
        </section>
      ) : null}
      {error ? (
        <p className="form-error" role="alert">
          {error}
        </p>
      ) : null}
    </form>
  );
}
