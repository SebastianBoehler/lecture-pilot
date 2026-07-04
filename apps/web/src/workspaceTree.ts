import type { CanvasBlock, CanvasDocument, CanvasSection, WorkspaceResource } from "./types";

export type WorkspaceTreeNode = {
  id: string;
  name: string;
  path: string;
  type: "folder" | "file";
  children: WorkspaceTreeNode[];
  tone?: "course" | "learner" | "memory";
  resource?: WorkspaceResource;
};

export function buildWorkspaceTree(canvasDocument: CanvasDocument): WorkspaceTreeNode[] {
  const courseCanvas = group("course-canvas", "Published course canvas", "course");
  const learnerFiles = group("learner-course-files", "Learner course files", "learner");
  const sourceMaterial = group("course-source-material", "Course source material", "course");
  const learnerMemory = group("learner-memory", "Learner memory", "memory");
  const courseCanvasDir = `.lecturepilot/courses/tenant-tuebingen/${canvasDocument.course_id}/canvas/lectures/${canvasDocument.lecture_id}`;
  const learnerDir = `.lecturepilot/users/<account>/courses/${canvasDocument.course_id}/lectures/${canvasDocument.lecture_id}`;
  addFile(courseCanvas.children, "index.md", canvasResource(canvasDocument, `${courseCanvasDir}/index.md`));
  addFile(courseCanvas.children, "canvas.json", {
    id: "compiled-canvas",
    kind: "canvas",
    label: "canvas.json",
    path: `${courseCanvasDir}/canvas.json`,
    displayPath: `${courseCanvasDir}/canvas.json`,
  });
  addCanvasSections(courseCanvas.children, learnerFiles.children, canvasDocument, courseCanvasDir, learnerDir);
  addCourseSource(sourceMaterial.children, canvasDocument);
  addCourseAssets(sourceMaterial.children, learnerFiles.children, canvasDocument);
  addLearnerFiles(learnerFiles.children, canvasDocument, learnerDir);
  addLearnerMemory(learnerMemory.children, canvasDocument);
  return [sourceMaterial, courseCanvas, learnerFiles, learnerMemory];
}

function addCanvasSections(
  courseRoots: WorkspaceTreeNode[],
  learnerRoots: WorkspaceTreeNode[],
  canvasDocument: CanvasDocument,
  courseCanvasDir: string,
  learnerDir: string,
) {
  let officialIndex = 1;
  let studentIndex = 90;
  for (const section of canvasDocument.sections) {
    const isStudent = isStudentSection(section);
    const folder = isStudent ? "student" : "sections";
    const prefix = isStudent ? studentIndex++ : officialIndex++;
    const fileName = `${String(prefix).padStart(2, "0")}-${safeFilename(section.id)}.md`;
    const roots = isStudent ? learnerRoots : courseRoots;
    const canvasDir = isStudent ? `${learnerDir}/canvas` : courseCanvasDir;
    const treePath = isStudent ? `canvas/${folder}/${fileName}` : `${folder}/${fileName}`;
    addFile(roots, treePath, {
      id: `canvas-section-${section.id}`,
      kind: "canvas",
      label: fileName,
      path: `${canvasDir}/${folder}/${fileName}`,
      displayPath: `${canvasDir}/${folder}/${fileName}`,
      detail: section.title,
    });
  }
}

function addCourseSource(roots: WorkspaceTreeNode[], canvasDocument: CanvasDocument) {
  const displayPath = `local-course-materials/${canvasDocument.course_id}/${canvasDocument.source_ref}`;
  addFile(roots, `source/${canvasDocument.source_ref}`, {
    id: "original-source",
    kind: "source",
    label: canvasDocument.source_ref,
    path: canvasDocument.source_ref,
    displayPath,
  });
}

function addCourseAssets(
  courseRoots: WorkspaceTreeNode[],
  learnerRoots: WorkspaceTreeNode[],
  canvasDocument: CanvasDocument,
) {
  for (const { asset, learnerOwned } of uniqueAssets(canvasDocument)) {
    const isVideo = asset.type === "video";
    const path = asset.asset_path ?? asset.caption ?? asset.id;
    const courseDisplayPath = isVideo
      ? `local-course-materials/${canvasDocument.course_id}/canvas/media/youtube/${safeFilename(path)}.json`
      : `local-course-materials/${canvasDocument.course_id}/images/${path}`;
    const learnerDisplayPath = `.lecturepilot/users/<account>/courses/${canvasDocument.course_id}/lectures/${canvasDocument.lecture_id}/canvas/${path}`;
    const displayPath = learnerOwned ? learnerDisplayPath : courseDisplayPath;
    const treePath = learnerOwned
      ? `canvas/${path}`
      : isVideo
        ? `media/youtube/${safeFilename(path)}.json`
        : `images/${path}`;
    addFile(learnerOwned ? learnerRoots : courseRoots, treePath, {
      id: `asset-${asset.id}`,
      kind: isVideo ? "video" : "asset",
      label: path.split("/").at(-1) ?? path,
      path,
      displayPath,
      detail: asset.caption ?? null,
      url: asset.asset_url,
    });
  }
}

function addLearnerFiles(
  roots: WorkspaceTreeNode[],
  canvasDocument: CanvasDocument,
  learnerDir: string,
) {
  addFile(roots, "canvas.json", {
    id: "learner-compiled-canvas",
    kind: "canvas",
    label: "canvas.json",
    path: `${learnerDir}/canvas.json`,
    displayPath: `${learnerDir}/canvas.json`,
    detail: "compiled learner overlay",
  });
  addFile(roots, "canvas/index.md", {
    id: "learner-canvas-index",
    kind: "canvas",
    label: "index.md",
    path: `${learnerDir}/canvas/index.md`,
    displayPath: `${learnerDir}/canvas/index.md`,
    detail: "current learner canvas view",
  });
  for (const section of canvasDocument.sections.filter(isStudentSection)) {
    for (const block of section.blocks) {
      if (block.type === "component" && block.component_ref) {
        addFile(roots, `canvas/components/${block.component_ref}`, {
          id: `component-${block.component_id ?? block.id}`,
          kind: "canvas",
          label: block.component_ref,
          path: block.component_ref,
          displayPath: `${learnerDir}/canvas/components/${block.component_ref}`,
          detail: block.caption ?? section.title,
        });
      }
    }
  }
}

function addLearnerMemory(roots: WorkspaceTreeNode[], canvasDocument: CanvasDocument) {
  const userRoot = ".lecturepilot/users/<account>";
  addMemoryFile(roots, "memories/global.md", `${userRoot}/memories/global.md`, "Global tutor notes");
  addMemoryFile(
    roots,
    "memories/preferences.json",
    `${userRoot}/memories/preferences.json`,
    "Structured preferences",
  );
  addMemoryFile(
    roots,
    `courses/${canvasDocument.course_id}/course.md`,
    `${userRoot}/courses/${canvasDocument.course_id}/memories/course.md`,
    "Course-specific tutor memory",
  );
}

function addMemoryFile(roots: WorkspaceTreeNode[], treePath: string, path: string, detail: string) {
  addFile(roots, treePath, {
    id: `memory-${safeFilename(path)}`,
    kind: "memory",
    label: path.split("/").at(-1) ?? path,
    path,
    displayPath: path,
    detail,
  });
}

function addFile(roots: WorkspaceTreeNode[], fullPath: string, resource: WorkspaceResource) {
  const parts = fullPath.split("/").filter(Boolean);
  let level = roots;
  let currentPath = "";
  for (const [index, part] of parts.entries()) {
    currentPath = currentPath ? `${currentPath}/${part}` : part;
    const isFile = index === parts.length - 1;
    let node = level.find((candidate) => candidate.name === part);
    if (!node) {
      node = {
        id: currentPath,
        name: part,
        path: currentPath,
        type: isFile ? "file" : "folder",
        children: [],
      };
      level.push(node);
    }
    if (isFile) {
      node.resource = resource;
    }
    level = node.children;
  }
}

function canvasResource(canvasDocument: CanvasDocument, displayPath: string): WorkspaceResource {
  return {
    id: "published-canvas",
    kind: "canvas",
    label: "index.md",
    path: displayPath,
    displayPath,
  };
}

function uniqueAssets(canvasDocument: CanvasDocument): { asset: CanvasBlock; learnerOwned: boolean }[] {
  const byPath = new Map<string, { asset: CanvasBlock; learnerOwned: boolean }>();
  for (const section of canvasDocument.sections) {
    for (const block of section.blocks) {
      const key = block.asset_path ?? block.asset_url;
      if (key && !byPath.has(key)) {
        byPath.set(key, {
          asset: block,
          learnerOwned: isStudentSection(section) || isLearnerAsset(block),
        });
      }
    }
  }
  return [...byPath.values()];
}

function group(id: string, name: string, tone: WorkspaceTreeNode["tone"]): WorkspaceTreeNode {
  return {
    id,
    name,
    path: id,
    type: "folder",
    tone,
    children: [],
  };
}

function isStudentSection(section: CanvasSection) {
  return section.source_ref === "student workspace" || section.id.startsWith("student-");
}

function isLearnerAsset(block: CanvasBlock) {
  return Boolean(block.asset_path?.startsWith("student-assets/") || block.asset_url?.startsWith("/workspace-assets/"));
}

function safeFilename(value: string) {
  return value.replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 120) || "section";
}
