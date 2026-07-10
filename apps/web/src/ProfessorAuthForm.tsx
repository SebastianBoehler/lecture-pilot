import { FormEvent, useState } from "react";

import { useI18n } from "./i18n";
import { loginProfessor, registerProfessor } from "./sessionApi";
import type { LoginSession } from "./types";

type ProfessorAuthMode = "login" | "register";

export function ProfessorAuthForm({
  onLogin,
}: {
  onLogin: (session: LoginSession) => void;
}) {
  const { t } = useI18n();
  const [mode, setMode] = useState<ProfessorAuthMode>("login");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  function changeMode(nextMode: ProfessorAuthMode) {
    setMode(nextMode);
    setPassword("");
    setPasswordConfirmation("");
    setError(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting || !email.trim() || !password) return;
    if (mode === "register" && password !== passwordConfirmation) {
      setError(t("login.professor.passwordMismatch"));
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      const session =
        mode === "register"
          ? await registerProfessor({
              display_name: displayName.trim(),
              email: email.trim(),
              password,
            })
          : await loginProfessor({ email: email.trim(), password });
      onLogin(session);
    } catch (authError) {
      setError(authError instanceof Error ? authError.message : t("login.professor.failed"));
    } finally {
      setPassword("");
      setPasswordConfirmation("");
      setIsSubmitting(false);
    }
  }

  const registration = mode === "register";
  const registrationReady =
    displayName.trim().length >= 2 && password.length >= 15 && passwordConfirmation.length > 0;

  return (
    <form autoComplete="on" className="login-form" method="post" onSubmit={submit}>
      <div className="professor-auth-heading">
        <strong>{t("login.professor.title")}</strong>
        <span>{t("login.professor.subtitle")}</span>
      </div>
      <div className="professor-auth-modes" aria-label={t("login.professor.modeLabel")}>
        <button
          className={!registration ? "is-active" : ""}
          type="button"
          onClick={() => changeMode("login")}
        >
          {t("login.professor.signIn")}
        </button>
        <button
          className={registration ? "is-active" : ""}
          type="button"
          onClick={() => changeMode("register")}
        >
          {t("login.professor.create")}
        </button>
      </div>
      {registration ? (
        <label>
          {t("login.professor.name")}
          <input
            autoComplete="name"
            id="name"
            maxLength={200}
            name="name"
            onChange={(event) => setDisplayName(event.target.value)}
            required
            value={displayName}
          />
        </label>
      ) : null}
      <label>
        {t("login.professor.email")}
        <input
          autoCapitalize="none"
          autoComplete="username"
          id="email"
          inputMode="email"
          name="email"
          onChange={(event) => setEmail(event.target.value)}
          required
          spellCheck={false}
          type="email"
          value={email}
        />
      </label>
      <label>
        {t("login.password")}
        <input
          aria-describedby={registration ? "professor-password-help" : undefined}
          autoComplete={registration ? "new-password" : "current-password"}
          id={registration ? "new-password" : "current-password"}
          maxLength={128}
          minLength={registration ? 15 : 1}
          name="password"
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
      </label>
      {registration ? (
        <>
          <label>
            {t("login.professor.confirmPassword")}
            <input
              autoComplete="new-password"
              aria-describedby="professor-password-help"
              id="new-password-confirmation"
              maxLength={128}
              minLength={15}
              name="password_confirmation"
              onChange={(event) => setPasswordConfirmation(event.target.value)}
              required
              type="password"
              value={passwordConfirmation}
            />
          </label>
          <p className="login-help" id="professor-password-help">
            {t("login.professor.passwordHelp")}
          </p>
        </>
      ) : null}
      <button
        className="login-submit-button"
        disabled={
          isSubmitting || !email.trim() || !password || (registration && !registrationReady)
        }
        type="submit"
      >
        {isSubmitting ? <span className="login-spinner" aria-hidden="true" /> : null}
        {registration
          ? t("login.professor.createSubmit")
          : t("login.professor.signInSubmit")}
      </button>
      {isSubmitting ? (
        <p className="login-status" role="status">
          {t("login.professor.status")}
        </p>
      ) : null}
      {error ? <p className="form-error" role="alert">{error}</p> : null}
    </form>
  );
}
