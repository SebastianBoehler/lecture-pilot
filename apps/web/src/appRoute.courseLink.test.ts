import { expect, it } from "vitest";

import { readAppRoute, requiresSession } from "./appRoute";

it("reads shared course and join links as public course-link routes", () => {
  expect(readAppRoute({ pathname: "/courses/medvis", search: "" })).toEqual({
    view: "course-link",
    courseId: "medvis",
  });
  expect(readAppRoute({ pathname: "/join/medvis/abc123", search: "" })).toEqual({
    view: "course-link",
    courseId: "medvis",
    code: "abc123",
  });
  expect(readAppRoute({ pathname: "/courses/medvis/lectures/lecture-01", search: "" }).view).toBe(
    "lesson",
  );
  expect(requiresSession("course-link")).toBe(false);
});
