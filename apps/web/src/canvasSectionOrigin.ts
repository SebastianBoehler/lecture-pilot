import type { CanvasSection } from "./types";

export function isLearnerGeneratedSection(section: CanvasSection) {
  return section.source_ref === "student workspace" || section.id.startsWith("student-");
}
