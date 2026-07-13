import { apiUrl } from "./api";
import { authRequestInit } from "./authz";
import type { LoginSession } from "./types";
import type { ProfessorUsageSummary } from "./usageTypes";

export async function getProfessorUsage(
  session: LoginSession,
  days: number,
): Promise<ProfessorUsageSummary> {
  let response: Response;
  try {
    response = await fetch(apiUrl(`/admin/usage?days=${days}`), authRequestInit(session));
  } catch {
    throw new Error("Cannot reach the local LecturePilot API. Is the backend running?");
  }
  const payload = await response.json();
  if (!response.ok) {
    const detail = typeof payload?.detail === "string" ? payload.detail : "Usage loading failed.";
    throw new Error(detail);
  }
  return payload as ProfessorUsageSummary;
}
