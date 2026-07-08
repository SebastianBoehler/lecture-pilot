import { FormEvent, useState } from "react";

import { loginWithTuebingen } from "./api";
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
      setError(loginError instanceof Error ? loginError.message : "Login failed.");
    } finally {
      setPassword("");
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-screen">
      <section className="login-panel" aria-labelledby="login-heading">
        <div className="login-copy">
          <h1 id="login-heading">Sign in with Uni Tübingen</h1>
          <p>Open your course workspace, catch up on lectures, and get ready for focused learning.</p>
        </div>

        <form className="login-form" onSubmit={submitLogin}>
          <label>
            ZDV username
            <input
              autoComplete="username"
              name="username"
              onChange={(event) => setUsername(event.target.value)}
              value={username}
            />
          </label>
          <label>
            Password
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
            {isSubmitting ? "Signing in" : "Continue with Uni Tübingen"}
          </button>
          {isSubmitting ? (
            <p className="login-status" role="status">
              Loading your course workspace. This can take a moment.
            </p>
          ) : null}
          <button className="secondary-button" disabled={isSubmitting} type="button" onClick={onOpenDemo}>
            Preview local demo
          </button>
          <button className="secondary-button" disabled={isSubmitting} type="button" onClick={onOpenProfessorDemo}>
            Preview professor account
          </button>
          {error ? <p className="form-error">{error}</p> : null}
        </form>
      </section>
    </main>
  );
}
