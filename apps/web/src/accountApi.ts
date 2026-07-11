import { apiUrl, readApiError } from "./api";
import { authRequestInit } from "./authz";
import type { LoginSession } from "./types";

export type ProfessorRequest = {
  id: string;
  user_id: string;
  username: string;
  email?: string | null;
  university_role?: string | null;
  status: "not_requested" | "pending" | "approved" | "rejected";
  requested_at: string;
  reviewed_at?: string | null;
};

export async function requestProfessorAccess(session: LoginSession) {
  return accountRequest(
    "/professor-requests",
    session,
    { method: "POST" },
    "Professor request failed.",
  );
}

export async function listProfessorRequests(session: LoginSession) {
  const response = await fetch(apiUrl("/platform/professor-requests"), authRequestInit(session));
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, "Professor requests failed to load."));
  return (Array.isArray(payload) ? payload : []) as ProfessorRequest[];
}

export async function reviewProfessorRequest(
  requestId: string,
  decision: "approve" | "reject",
  session: LoginSession,
) {
  return accountRequest(
    `/platform/professor-requests/${requestId}/${decision}`,
    session,
    { method: "POST" },
    "Professor request review failed.",
  );
}

async function accountRequest(
  path: string,
  session: LoginSession,
  init: RequestInit,
  fallback: string,
) {
  const response = await fetch(apiUrl(path), authRequestInit(session, init));
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(readApiError(payload, fallback));
  return payload as ProfessorRequest;
}
