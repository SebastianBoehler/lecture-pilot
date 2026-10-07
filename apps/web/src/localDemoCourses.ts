import type { LoginSession, UniversityCourse } from "./types";

export function withLocalDemoCourses(session: LoginSession, courses: UniversityCourse[]) {
  if (
    !import.meta.env.DEV ||
    session.username !== "local-demo" ||
    session.auth_transport !== "dev_headers" ||
    session.access_token ||
    !session.roles?.includes("student") ||
    session.roles.some((role) => role !== "student")
  ) {
    return session;
  }
  const currentIds = session.courses.map((course) => course.id).sort();
  const discoveredIds = courses.map((course) => course.id).sort();
  if (JSON.stringify(currentIds) === JSON.stringify(discoveredIds)) return session;
  return { ...session, courses };
}
