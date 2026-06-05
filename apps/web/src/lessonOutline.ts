import type { DocumentAnchorId } from "./types";

export type OutlineItem = {
  id: DocumentAnchorId;
  title: string;
  kind: "section" | "material" | "check";
};

export const documentOutlineItems: OutlineItem[] = [
  { id: "source-packet", title: "Course source packet", kind: "material" },
  { id: "learning-goals", title: "Learning goals", kind: "section" },
  { id: "artifact-counter", title: "Concept counter", kind: "check" },
  { id: "feature-maps", title: "Feature maps", kind: "section" },
  { id: "artifact-diagram", title: "Feature map diagram", kind: "material" },
  { id: "artifact-video", title: "Professor-selected video", kind: "material" },
  { id: "kernel-trick", title: "Kernel trick", kind: "section" },
  { id: "artifact-code", title: "Runnable code cell", kind: "material" },
  { id: "skill-check", title: "Skill check", kind: "check" },
  { id: "artifact-quiz", title: "Micro quiz", kind: "check" },
  { id: "artifact-playground", title: "Kernel playground", kind: "material" },
  { id: "failure-mode", title: "Common failure mode", kind: "section" },
  { id: "artifact-summary", title: "Generated summary", kind: "material" },
];
