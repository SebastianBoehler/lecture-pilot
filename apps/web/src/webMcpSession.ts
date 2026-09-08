import { isStudentAccount } from "./authz";
import type { LoginSession } from "./types";

// Registration eligibility only. Every execution must still verify with /me.
export function hasStudentWebMcpCredentials(session: LoginSession | null) {
  return (
    isStudentAccount(session) &&
    Boolean(session?.auth_transport === "cookie" || session?.access_token)
  );
}
