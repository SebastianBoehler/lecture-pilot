import { apiUrl, readApiError } from "../shared/api";

export type AccountMode = "login" | "register" | "forgot" | "verify" | "reset";

export function readAccountLink(): { mode: AccountMode; token: string } {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const action = params.get("auth");
  const token = params.get("token") ?? "";
  return { mode: token && (action === "verify" || action === "reset") ? action : "login", token };
}

export async function accountAction(
  mode: Exclude<AccountMode, "login">,
  input: { email: string; password: string; token: string },
): Promise<void> {
  const paths = {
    register: "/auth/register",
    forgot: "/auth/password-reset",
    verify: "/auth/verify",
    reset: "/auth/password-reset/confirm",
  };
  const bodies = {
    register: { email: input.email, password: input.password },
    forgot: { email: input.email },
    verify: { token: input.token },
    reset: { token: input.token, password: input.password },
  };
  const response = await fetch(apiUrl(paths[mode]), {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bodies[mode]),
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, "Account request failed."));
}
