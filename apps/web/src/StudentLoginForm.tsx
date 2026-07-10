import { FormEvent, useState } from "react";

import { useI18n } from "./i18n";
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
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!username.trim() || !password || isSubmitting) return;
    setError(null);
    setIsSubmitting(true);
    try {
      onLogin(
        await loginWithTuebingen({
          username: username.trim(),
          password,
        }),
      );
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : t("login.failed"));
    } finally {
      setPassword("");
      setIsSubmitting(false);
    }
  }

  return (
    <form className="login-form" onSubmit={submitLogin}>
      <label>
        {t("login.username")}
        <input
          autoComplete="username"
          maxLength={120}
          name="username"
          onChange={(event) => setUsername(event.target.value)}
          required
          value={username}
        />
      </label>
      <label>
        {t("login.password")}
        <input
          autoComplete="current-password"
          maxLength={500}
          name="password"
          onChange={(event) => setPassword(event.target.value)}
          required
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
