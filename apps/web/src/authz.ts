import type { LoginSession, TenantRole } from "./types";

const courseManagementRoles = new Set<TenantRole>(["tenant_admin", "professor"]);

export function canManageCourses(session: LoginSession | null) {
  return Boolean(courseManagerRole(session));
}

export function courseManagerHeaders(session: LoginSession) {
  const role = courseManagerRole(session);
  if (!role) {
    throw new Error("Course management requires a professor account.");
  }
  return authHeaders(session, role);
}

export function authHeaders(session: LoginSession, role = session.roles?.[0] ?? "student") {
  return {
    "X-Tenant-Id": session.tenant_id ?? "tenant-tuebingen",
    "X-User-Id": session.username,
    "X-User-Role": role,
  };
}

function courseManagerRole(session: LoginSession | null) {
  return session?.roles?.find((role) => courseManagementRoles.has(role)) ?? null;
}
