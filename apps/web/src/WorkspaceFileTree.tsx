import {
  ChevronDown,
  ChevronRight,
  FileCode2,
  FileImage,
  FileJson,
  FileText,
  Folder,
} from "lucide-react";
import { useEffect, useMemo, useState, type CSSProperties } from "react";

import type { WorkspaceResource } from "./types";
import type { WorkspaceTreeNode } from "./workspaceTree";

export function WorkspaceFileTree({
  nodes,
  selectedResource,
  onSelectResource,
}: {
  nodes: WorkspaceTreeNode[];
  selectedResource: WorkspaceResource | null;
  onSelectResource: (resource: WorkspaceResource) => void;
}) {
  const defaultExpanded = useMemo(() => new Set(folderIds(nodes)), [nodes]);
  const [expanded, setExpanded] = useState(defaultExpanded);

  useEffect(() => {
    setExpanded(defaultExpanded);
  }, [defaultExpanded]);

  function toggle(nodeId: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  }

  return (
    <div className="workspace-tree" role="tree" aria-label="Workspace file tree">
      {nodes.map((node) => (
        <TreeNode
          depth={0}
          expanded={expanded}
          key={node.id}
          node={node}
          selectedResource={selectedResource}
          onSelectResource={onSelectResource}
          onToggle={toggle}
        />
      ))}
    </div>
  );
}

function TreeNode({
  node,
  depth,
  expanded,
  selectedResource,
  onSelectResource,
  onToggle,
}: {
  node: WorkspaceTreeNode;
  depth: number;
  expanded: Set<string>;
  selectedResource: WorkspaceResource | null;
  onSelectResource: (resource: WorkspaceResource) => void;
  onToggle: (nodeId: string) => void;
}) {
  if (node.type === "folder") {
    const isExpanded = expanded.has(node.id);
    return (
      <div role="group">
        <button
          aria-expanded={isExpanded}
          aria-label={`${isExpanded ? "Collapse" : "Expand"} ${node.name}`}
          className={folderClassName(node)}
          style={depthStyle(depth)}
          type="button"
          onClick={() => onToggle(node.id)}
        >
          {isExpanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
          <Folder size={15} />
          <span>{node.name}</span>
        </button>
        {isExpanded
          ? node.children.map((child) => (
              <TreeNode
                depth={depth + 1}
                expanded={expanded}
                key={child.id}
                node={child}
                selectedResource={selectedResource}
                onSelectResource={onSelectResource}
                onToggle={onToggle}
              />
            ))
          : null}
      </div>
    );
  }

  const isSelected = Boolean(node.resource && isSameResource(selectedResource, node.resource));
  return (
    <button
      aria-label={`Open ${node.name}`}
      aria-pressed={isSelected}
      className={isSelected ? "workspace-tree-row is-file is-selected" : "workspace-tree-row is-file"}
      style={depthStyle(depth)}
      type="button"
      onClick={() => node.resource && onSelectResource(node.resource)}
    >
      {fileIcon(node.resource, node.name)}
      <span>{node.name}</span>
    </button>
  );
}

function folderIds(nodes: WorkspaceTreeNode[]): string[] {
  return nodes.flatMap((node) => [
    ...(node.type === "folder" ? [node.id] : []),
    ...folderIds(node.children),
  ]);
}

function depthStyle(depth: number) {
  return { "--tree-depth": depth } as CSSProperties;
}

function isSameResource(left: WorkspaceResource | null, right: WorkspaceResource) {
  return Boolean(
    left &&
      (left.path === right.path ||
        left.id === right.id ||
        (left.url && right.url && left.url === right.url)),
  );
}

function folderClassName(node: WorkspaceTreeNode) {
  return [
    "workspace-tree-row",
    "is-folder",
    node.tone ? `is-${node.tone}` : "",
  ].filter(Boolean).join(" ");
}

function fileIcon(resource: WorkspaceResource | undefined, name: string) {
  if (resource?.kind === "asset") return <FileImage size={15} />;
  if (name.endsWith(".json")) return <FileJson size={15} />;
  if (name.endsWith(".tex")) return <FileCode2 size={15} />;
  return <FileText size={15} />;
}
