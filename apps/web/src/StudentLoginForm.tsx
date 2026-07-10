import { FormEvent, useState } from "react";

import { useI18n } from "./i18n";
import { useRememberedLoginIdentifier } from "./loginPreferences";
import { loginWithTuebingen } from "./sessionApi";
import type { LoginSession } from "./types";

export function StudentLoginForm({
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
  } = useRememberedLoginIdentifier("student");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

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
          id="current-password"
          maxLength={500}
          name="password"
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
      </label>
      <div className="login-remember">
        <label className="login-checkbox">
          <input
            aria-describedby="student-remember-help"
            checked={rememberUsername}
            name="remember_username"
            onChange={(event) => setRememberUsername(event.target.checked)}
            type="checkbox"
          />
          <span>{t("login.rememberUsername")}</span>
        </label>
        <p className="login-help" id="student-remember-help">
          {t("login.rememberHelp")}
        </p>
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
        <div className="login-demo-actions">
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
      ) : null}
      {error ? <p className="form-error" role="alert">{error}</p> : null}
    </form>
  );
}
