import { describe, expect, it } from "vitest";
import { localDemoSession } from "./appDefaults";
import { withLocalDemoCourses } from "./localDemoCourses";

const courses = [
  ...localDemoSession.courses,
  { ...localDemoSession.courses[0], id: "local-nlp", title: "Natural Language Processing" },
];

describe("local demo enrollment", () => {
  it("uses actual discovered local courses for the demo student's enrollment headers", () => {
    const session = withLocalDemoCourses(localDemoSession, courses);
    expect(session.courses).toEqual(courses);
  });
  it("leaves an already current demo session unchanged", () => {
    const session = { ...localDemoSession, courses };
    expect(withLocalDemoCourses(session, courses)).toBe(session);
  });
  it("preserves authenticated university enrollment", () => {
    const session = { ...localDemoSession, auth_transport: "cookie" as const };
    expect(withLocalDemoCourses(session, courses)).toBe(session);
  });
  it("preserves other development users and professor sessions", () => {
    const other = { ...localDemoSession, username: "another-student" };
    expect(withLocalDemoCourses(other, courses)).toBe(other);
    const professor = { ...localDemoSession, roles: ["professor" as const] };
    expect(withLocalDemoCourses(professor, courses)).toBe(professor);
  });
});
