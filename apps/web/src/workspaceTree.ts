import type { CanvasBlock, CanvasDocument, CanvasSection, WorkspaceResource } from "./types";

export type WorkspaceTreeNode = {
  id: string;
  name: string;
  path: string;
  type: "folder" | "file";
  children: WorkspaceTreeNode[];
  resource?: WorkspaceResource;
};

export function buildWorkspaceTree(canvasDocument: CanvasDocument): WorkspaceTreeNode[] {
  const roots: WorkspaceTreeNode[] = [];
  const canvasDir = canvasDocument.workspace_path.replace(/\/index\.md$/, "");
  const lectureDir = canvasDir.replace(/\/canvas$/, "");
  addFile(roots, canvasDocument.workspace_path, canvasResource(canvasDocument));
  addFile(roots, `${lectureDir}/canvas.json`, {
    id: "compiled-canvas",
    kind: "canvas",
    label: "canvas.json",
    path: `${lectureDir}/canvas.json`,
  });
  addCanvasSections(roots, canvasDocument, canvasDir);
  addCourseSource(roots, canvasDocument);
  addCourseAssets(roots, canvasDocument);
  return roots;
}

function addCanvasSections(
  roots: WorkspaceTreeNode[],
  canvasDocument: CanvasDocument,
  canvasDir: string,
) {
  let officialIndex = 1;
  let studentIndex = 90;
  for (const section of canvasDocument.sections) {
    const isStudent = isStudentSection(section);
    const folder = isStudent ? "student" : "sections";
    const prefix = isStudent ? studentIndex++ : officialIndex++;
    const fileName = `${String(prefix).padStart(2, "0")}-${safeFilename(section.id)}.md`;
    addFile(roots, `${canvasDir}/${folder}/${fileName}`, {
      id: `canvas-section-${section.id}`,
      kind: "canvas",
      label: fileName,
      path: `${canvasDir}/${folder}/${fileName}`,
      detail: section.title,
    });
  }
}

function addCourseSource(roots: WorkspaceTreeNode[], canvasDocument: CanvasDocument) {
  const displayPath = `local-course-materials/${canvasDocument.course_id}/${canvasDocument.source_ref}`;
  addFile(roots, displayPath, {
    id: "original-source",
    kind: "source",
    label: canvasDocument.source_ref,
    path: canvasDocument.source_ref,
    displayPath,
  });
}

function addCourseAssets(roots: WorkspaceTreeNode[], canvasDocument: CanvasDocument) {
  const assets = uniqueAssets(canvasDocument);
  for (const asset of assets) {
    const isVideo = asset.type === "video";
    const path = asset.asset_path ?? asset.caption ?? asset.id;
    const displayPath = isVideo
      ? `local-course-materials/${canvasDocument.course_id}/canvas/media/youtube/${safeFilename(path)}.json`
      : `local-course-materials/${canvasDocument.course_id}/images/${path}`;
    addFile(roots, displayPath, {
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

function canvasResource(canvasDocument: CanvasDocument): WorkspaceResource {
  return {
    id: "student-canvas",
    kind: "canvas",
    label: "index.md",
    path: canvasDocument.workspace_path,
    displayPath: canvasDocument.workspace_path,
  };
}

function uniqueAssets(canvasDocument: CanvasDocument): CanvasBlock[] {
  const byPath = new Map<string, CanvasBlock>();
  for (const section of canvasDocument.sections) {
    for (const block of section.blocks) {
      const key = block.asset_path ?? block.asset_url;
      if (key && !byPath.has(key)) byPath.set(key, block);
    }
  }
  return [...byPath.values()];
}

function isStudentSection(section: CanvasSection) {
  return section.source_ref === "student workspace" || section.id.startsWith("student-");
}

function safeFilename(value: string) {
  return value.replace(/[^a-zA-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 120) || "section";
}
