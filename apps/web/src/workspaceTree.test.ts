import { describe, expect, it } from "vitest";

import type { CanvasDocument, WorkspaceResource } from "./types";
import { buildWorkspaceTree } from "./workspaceTree";

describe("workspace tree", () => {
  it("groups course, learner, and memory resources by ownership", () => {
    const tree = buildWorkspaceTree(documentWithStudentSection());
    const groupNames = tree.map((node) => node.name);

    expect(groupNames).toEqual([
      "Course source material",
      "Published course canvas",
      "Learner course files",
      "Learner memory",
    ]);
    expect(nodePaths(tree[1])).toContain("sections/01-official-topic.md");
    expect(nodePaths(tree[2])).toContain("canvas/student/90-student-note.md");
    expect(nodePaths(tree[3])).toContain("memories/preferences.json");
    expect(pathsFor(tree[1])).toContain(
      ".lecturepilot/courses/tenant-tuebingen/martius-ml/canvas/lectures/lecture-03/sections/01-official-topic.md",
    );
    expect(pathsFor(tree[2])).toEqual(
      expect.arrayContaining([
        ".lecturepilot/users/<account>/courses/martius-ml/lectures/lecture-03/canvas/student/90-student-note.md",
        ".lecturepilot/users/<account>/courses/martius-ml/lectures/lecture-03/canvas/student-assets/student-diagram.png",
        ".lecturepilot/users/<account>/courses/martius-ml/lectures/lecture-03/canvas.json",
      ]),
    );
    expect(pathsFor(tree[3])).toEqual(
      expect.arrayContaining([
        ".lecturepilot/users/<account>/memories/global.md",
        ".lecturepilot/users/<account>/memories/memory-trace.jsonl",
        ".lecturepilot/users/<account>/memories/preferences.json",
        ".lecturepilot/users/<account>/courses/martius-ml/memories/course.md",
        ".lecturepilot/users/<account>/courses/martius-ml/memories/memory-trace.jsonl",
      ]),
    );
    expect(resourceFor(tree, "sections/01-official-topic.md")).toMatchObject({
      sectionId: "official-topic",
    });
    expect(resourceFor(tree, "sections/01-official-topic.md")).not.toHaveProperty("blockId");
    expect(resourceFor(tree, "canvas/student-assets/student-diagram.png")).toMatchObject({
      sectionId: "student-note",
      blockId: "student-image",
    });
  });
});

function nodePaths(node: ReturnType<typeof buildWorkspaceTree>[number]): string[] {
  return [node.path, ...node.children.flatMap(nodePaths)];
}

function pathsFor(node: ReturnType<typeof buildWorkspaceTree>[number]): string[] {
  return [
    node.resource?.displayPath ?? node.resource?.path ?? "",
    ...node.children.flatMap(pathsFor),
  ].filter(Boolean);
}

function resourceFor(
  nodes: ReturnType<typeof buildWorkspaceTree>,
  path: string,
): WorkspaceResource | undefined {
  const resources = nodes.flatMap((node) => collectResources(node));
  return resources.find(
    (resource) => resource.displayPath?.endsWith(path) || resource.path.endsWith(path),
  );
}

function collectResources(
  node: ReturnType<typeof buildWorkspaceTree>[number],
): WorkspaceResource[] {
  return [...(node.resource ? [node.resource] : []), ...node.children.flatMap(collectResources)];
}

function documentWithStudentSection(): CanvasDocument {
  return {
    id: "martius-ml-lecture-03",
    course_id: "martius-ml",
    lecture_id: "lecture-03",
    title: "Bayesian Decision Theory",
    source_kind: "generated",
    source_ref: "Lecture03-eng.tex",
    workspace_path:
      ".lecturepilot/users/hash/courses/martius-ml/lectures/lecture-03/canvas/index.md",
    sections: [
      {
        id: "official-topic",
        title: "Official topic",
        source_ref: "Lecture03-eng.tex frames 1-2",
        blocks: [{ id: "official-p", type: "paragraph", text: "Official source.", items: [] }],
      },
      {
        id: "student-note",
        title: "Student note",
        source_ref: "student workspace",
        blocks: [
          {
            id: "student-image",
            type: "asset",
            asset_path: "student-assets/student-diagram.png",
            asset_url:
              "/workspace-assets/martius-ml/lecture-03/hash/student-assets/student-diagram.png",
            caption: "Student diagram",
            items: [],
          },
        ],
      },
    ],
  };
}
