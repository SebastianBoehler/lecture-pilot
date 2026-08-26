import type { CourseSourceRoutingManifest, SourceBundleManifest } from "./types";

export type FixtureScope = "full-course" | "single-lecture";

export function sourceBundle(scope: FixtureScope): SourceBundleManifest {
  if (scope === "full-course")
    return {
      course_id: "demo-ml-course",
      files: [
        { path: "Lecture01-eng.tex", kind: "latex", size_bytes: 1000 },
        { path: "Lecture02-eng.tex", kind: "latex", size_bytes: 1000 },
      ],
      counts_by_kind: { latex: 2 },
      supported_uploads: supportedUploads(),
    };
  return {
    course_id: "demo-ml-course",
    files: [
      { path: "Lecture03-eng.tex", kind: "latex", size_bytes: 1000 },
      { path: "Ch3/Venn_C-X_1.pdf", kind: "pdf", size_bytes: 2000 },
      { path: "videos/demo.mp4", kind: "video", size_bytes: 3000 },
    ],
    counts_by_kind: { latex: 1, pdf: 1, video: 1 },
    supported_uploads: supportedUploads(),
  };
}

export function sourceRouting(
  confirmed: boolean,
  scope: FixtureScope,
): CourseSourceRoutingManifest {
  return {
    confirmed,
    course_id: "demo-ml-course",
    source_revision: "a".repeat(64),
    routes:
      scope === "full-course"
        ? [
            route("Lecture01-eng.tex", "lecture-01", "b"),
            route("Lecture02-eng.tex", "lecture-02", "c"),
          ]
        : [
            route("Lecture03-eng.tex", "lecture-03", "b"),
            route("Ch3/Venn_C-X_1.pdf", "lecture-03", "c", "pdf"),
            route("videos/demo.mp4", "lecture-03", "d", "video"),
          ],
  };
}

export function hasConfirmedLectureRoute(routing: CourseSourceRoutingManifest, lectureId: string) {
  return Boolean(
    routing.confirmed &&
    routing.routes.some((route) => route.role === "lecture" && route.lecture_id === lectureId),
  );
}

export function workspaceScope(init?: RequestInit): FixtureScope {
  const body = JSON.parse(String(init?.body ?? "{}"));
  return body.target === "full-course" ? "full-course" : "single-lecture";
}

export function savedWorkspaceScope(): FixtureScope | null {
  try {
    const saved = JSON.parse(
      window.sessionStorage.getItem("lecturepilot.professor-builder.current") ?? "null",
    );
    return saved?.setup?.target === "full-course" ? "full-course" : null;
  } catch {
    return null;
  }
}

export function lectureSourcePath(lectureId: string) {
  const number = lectureId.match(/lecture-(\d+)/)?.[1] ?? "03";
  return `Lecture${number}-eng.tex`;
}

function route(
  path: string,
  lectureId: string,
  sha: string,
  kind: "latex" | "pdf" | "video" = "latex",
) {
  return { kind, lecture_id: lectureId, path, role: "lecture" as const, sha256: sha.repeat(64) };
}

function supportedUploads() {
  return [
    { suffix: ".md", kind: "markdown" as const, max_bytes: 5 * 1024 * 1024 },
    { suffix: ".tex", kind: "latex" as const, max_bytes: 10 * 1024 * 1024 },
  ];
}
