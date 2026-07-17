import type { LearnerWorkspaceMode, LoginSession, TenantRole } from "./types";

export const LECTUREPILOT_CLIENT_CONTRACT = "1";

const courseManagementRoles = new Set<TenantRole>(["professor"]);

export function canManageCourses(session: LoginSession | null) {
  return Boolean(courseManagerRole(session));
}

export function isStudentAccount(session: LoginSession | null) {
  return Boolean(session && (session.account_type ?? "student") === "student");
}

export function courseManagerHeaders(session: LoginSession): Record<string, string> {
  const role = courseManagerRole(session);
  if (!role) {
    throw new Error("Course management requires a professor account.");
  }
  return authHeaders(session, role);
}

export function authHeaders(
  session: LoginSession,
  role = session.roles?.[0] ?? "student",
): Record<string, string> {
  if (session.access_token) {
    return {
      Authorization: `Bearer ${session.access_token}`,
    };
  }
  if (session.auth_transport === "cookie") {
    return {};
  }
  return {
    "X-Course-Ids": (session.courses ?? []).map((course) => course.id).join(","),
    "X-Tenant-Id": session.tenant_id ?? "tenant-tuebingen",
    "X-User-Id": session.username,
    "X-User-Role": role,
  };
}

export function authRequestInit(session: LoginSession, init: RequestInit = {}): RequestInit {
  const headers = new Headers(authHeaders(session));
  new Headers(init.headers).forEach((value, key) => {
    headers.set(key, value);
  });
  headers.set("X-LecturePilot-Client-Contract", LECTUREPILOT_CLIENT_CONTRACT);
  const method = (init.method ?? "GET").toUpperCase();
  if (
    session.auth_transport === "cookie" &&
    !["GET", "HEAD", "OPTIONS", "TRACE"].includes(method) &&
    session.csrf_token
  ) {
    headers.set("X-CSRF-Token", session.csrf_token);
  }
  return {
    ...init,
    credentials: "include",
    headers,
  };
}

export function learnerRequestInit(
  session: LoginSession,
  mode: LearnerWorkspaceMode,
  init: RequestInit = {},
): RequestInit {
  const headers = new Headers(init.headers);
  if (mode === "professor-preview") {
    headers.set("X-LecturePilot-Learner-Preview", "professor");
  }
  return authRequestInit(session, { ...init, headers });
}

function courseManagerRole(session: LoginSession | null) {
  return session?.roles?.find((role) => courseManagementRoles.has(role)) ?? null;
}
