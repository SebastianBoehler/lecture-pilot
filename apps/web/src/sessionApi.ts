import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type { LoginSession } from "./types";

type TuebingenLoginInput = {
  username: string;
  password: string;
};

export async function loginWithTuebingen(input: TuebingenLoginInput): Promise<LoginSession> {
  let response: Response;
  try {
    response = await fetch(apiUrl("/auth/login"), {
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
