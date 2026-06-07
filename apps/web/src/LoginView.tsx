import { FormEvent, useState } from "react";

import { loginWithTuebingen } from "./api";
import type { LoginSession } from "./types";

export function LoginView({
  onLogin,
  onOpenDemo,
  onOpenProfessor,
}: {
  onLogin: (session: LoginSession) => void;
  onOpenDemo: () => void;
  onOpenProfessor: () => void;
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
          <p className="section-label">TUE API wrapper</p>
          <h1 id="login-heading">Sign in with Uni Tübingen</h1>
          <p>
            Credentials are sent to the local LecturePilot API and used for the Alma timetable
            lookup.
          </p>
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
          <button disabled={isSubmitting || !username.trim() || !password} type="submit">
            {isSubmitting ? "Connecting" : "Connect to TUE API"}
          </button>
          <button className="secondary-button" type="button" onClick={onOpenDemo}>
            Preview local demo
          </button>
          <button className="secondary-button" type="button" onClick={onOpenProfessor}>
            Professor course builder
          </button>
          {error ? <p className="form-error">{error}</p> : null}
        </form>
      </section>
    </main>
  );
}
