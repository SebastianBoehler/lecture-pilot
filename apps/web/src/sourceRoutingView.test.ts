import { describe, expect, it } from "vitest";

import { hasNoAssignedEvidence } from "./sourceRoutingView";
import type { CourseSourceRoute } from "./types";

describe("source routing readiness", () => {
  it("allows confirmed routing to exclude irrelevant supplemental files", () => {
    const routes = [
      {
        path: "Lecture01.pdf",
        kind: "pdf",
        role: "lecture",
        lecture_id: "lecture-01",
      },
      {
        path: "code/unrelated-demo.ipynb",
        kind: "notebook",
        role: "excluded",
        lecture_id: null,
      },
    ] as CourseSourceRoute[];

    expect(hasNoAssignedEvidence(routes)).toBe(false);
  });
});
