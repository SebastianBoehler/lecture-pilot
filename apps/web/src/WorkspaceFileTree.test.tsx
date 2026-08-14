import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { WorkspaceFileTree } from "./WorkspaceFileTree";
import type { WorkspaceResource } from "./types";
import type { WorkspaceTreeNode } from "./workspaceTree";

describe("WorkspaceFileTree", () => {
  it("keeps sibling files visible and marks only the current file", () => {
    const selectedResource = sourceResource("reading.pdf", "slides/week-03/reading.pdf");
    render(
      <WorkspaceFileTree
        nodes={treeNodes(selectedResource)}
        selectedResource={selectedResource}
        onSelectResource={vi.fn()}
      />,
    );

    const explorer = screen.getByRole("navigation", { name: /workspace file tree/i });
    const selected = within(explorer).getByRole("button", { name: /open reading\.pdf/i });
    const sibling = within(explorer).getByRole("button", { name: /open exercise\.tex/i });

    expect(selected).toHaveAttribute("aria-current", "true");
    expect(sibling).not.toHaveAttribute("aria-current");
    expect(
      within(explorer).getByRole("button", { name: /collapse slides \/ week-03/i }),
    ).toBeVisible();
  });

  it("keeps compact folders collapsible with native button behavior", async () => {
    const user = userEvent.setup();
    render(
      <WorkspaceFileTree
        nodes={treeNodes(null)}
        selectedResource={null}
        onSelectResource={vi.fn()}
      />,
    );
    const explorer = screen.getByRole("navigation", { name: /workspace file tree/i });
    const folder = within(explorer).getByRole("button", {
      name: /collapse slides \/ week-03/i,
    });

    await user.click(folder);

    expect(folder).toHaveAttribute("aria-expanded", "false");
    expect(within(explorer).queryByRole("button", { name: /open reading\.pdf/i })).toBeNull();
    expect(within(explorer).getByRole("button", { name: /open overview\.md/i })).toBeVisible();
  });
});

function treeNodes(selectedResource: WorkspaceResource | null): WorkspaceTreeNode[] {
  return [
    {
      id: "sources",
      name: "Course source material",
      path: "sources",
      type: "folder",
      tone: "course",
      children: [
        {
          id: "slides",
          name: "slides",
          path: "slides",
          type: "folder",
          children: [
            {
              id: "slides/week-03",
              name: "week-03",
              path: "slides/week-03",
              type: "folder",
              children: [
                fileNode(
                  selectedResource ?? sourceResource("reading.pdf", "slides/week-03/reading.pdf"),
                ),
                fileNode(sourceResource("exercise.tex", "slides/week-03/exercise.tex")),
              ],
            },
          ],
        },
        fileNode(sourceResource("overview.md", "overview.md")),
      ],
    },
  ];
}

function fileNode(resource: WorkspaceResource): WorkspaceTreeNode {
  return {
    id: resource.path,
    name: resource.label,
    path: resource.path,
    type: "file",
    children: [],
    resource,
  };
}

function sourceResource(label: string, path: string): WorkspaceResource {
  return { id: `source-${path}`, kind: "source", label, path };
}
