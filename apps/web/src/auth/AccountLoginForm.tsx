import { FormEvent, useState } from "react";

import { useI18n } from "../i18n/i18n";
import { useRememberedLoginIdentifier } from "./loginPreferences";
import { loginWithPassword } from "./sessionApi";
import type { LoginSession } from "../shared/types";
import { accountAction, readAccountLink, type AccountMode } from "./accountActions";
import { useVersionUpdateActivity } from "../shell/VersionUpdateBoundary";

export function AccountLoginForm({
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
  const [link] = useState(readAccountLink);
  const [mode, setMode] = useState<AccountMode>(link.mode);
  const [notice, setNotice] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [initialUsername] = useState(username);
  useVersionUpdateActivity(isSubmitting || Boolean(password) || username !== initialUsername);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;
    setError(null);
    setIsSubmitting(true);
    try {
      if (mode === "login") {
        const session = await loginWithPassword({ email: username.trim(), password });
        persistRememberedIdentifier();
        onLogin(session);
      } else {
        await accountAction(mode, { email: username.trim(), password, token: link.token });
        setNotice(t(mode === "verify" || mode === "reset" ? "account.updated" : "account.sent"));
        if (mode === "verify" || mode === "reset") {
          window.history.replaceState(null, "", window.location.pathname + window.location.search);
          setMode("login");
        }
      }
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : t("login.failed"));
    } finally {
      setPassword("");
      setIsSubmitting(false);
    }
  }

  return (
    <form autoComplete="on" className="login-form" method="post" onSubmit={submitLogin}>
      {mode !== "verify" && mode !== "reset" ? (
        <label>
          {t("login.username")}
          <input
            autoCapitalize="none"
            autoComplete="username"
            id="username"
            type="email"
            maxLength={200}
            name="username"
            onChange={(event) => setUsername(event.target.value)}
            required
            spellCheck={false}
            value={username}
          />
        </label>
      ) : null}
      {mode !== "verify" && mode !== "forgot" ? (
        <label>
          {t("login.password")}
          <input
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            id="account-password"
            minLength={mode === "login" ? 1 : 12}
            maxLength={500}
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>
      ) : null}
      {mode === "login" ? (
        <div className="login-checkbox">
          <input
            aria-describedby="account-remember-help"
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
            <span className="login-help" id="account-remember-help">
              {t("login.rememberHelp")}
            </span>
          </span>
        </div>
      ) : null}
      <button className="login-submit-button" disabled={isSubmitting} type="submit">
        {isSubmitting ? <span className="login-spinner" aria-hidden="true" /> : null}
        {isSubmitting
          ? t("login.submitting")
          : t(mode === "login" ? "login.submit" : `account.${mode}`)}
      </button>
      {isSubmitting ? (
        <p className="login-status" role="status">
          {t("login.status")}
        </p>
      ) : null}
      <div className="login-demo-buttons">
        {(["login", "register", "forgot"] as const)
          .filter((item) => item !== mode)
          .map((item) => (
            <button
              className={item === "forgot" ? "tertiary-button" : "secondary-button"}
              type="button"
              disabled={isSubmitting}
              key={item}
              onClick={() => {
                setMode(item);
                setError(null);
                setNotice(null);
                setPassword("");
              }}
            >
              {t(item === "login" ? "login.submit" : `account.${item}`)}
            </button>
          ))}
      </div>
      {notice ? <p role="status">{notice}</p> : null}
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
