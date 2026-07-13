import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type { LoginSession } from "./types";

type TuebingenLoginInput = {
  username: string;
  password: string;
};

export async function loginWithTuebingen(input: TuebingenLoginInput): Promise<LoginSession> {
  return createSession("/auth/login", input);
}

async function createSession(path: string, input: object): Promise<LoginSession> {
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    });
  } catch {
    throw new Error(
      `Cannot reach the local LecturePilot API at ${apiUrl("")}. Is the backend running?`,
    );
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(readApiError(payload, "Login failed."));
  }

  return { ...(payload as LoginSession), access_token: null, auth_transport: "cookie" };
}

export async function logoutSession(session: LoginSession): Promise<void> {
  await fetch(apiUrl("/auth/logout"), {
    ...authRequestInit(session, { method: "POST" }),
  }).catch(() => undefined);
}

export async function refreshSession(
  session: LoginSession,
  signal?: AbortSignal,
): Promise<LoginSession> {
  const response = await fetch(apiUrl("/me"), authRequestInit(session, { signal }));
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(readApiError(payload, "Account refresh failed."));
  }
  const account = payload as Partial<LoginSession>;
  return {
    ...session,
    ...account,
    csrf_token: account.csrf_token ?? session.csrf_token,
  };
}
