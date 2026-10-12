export type PrerequisiteNode = {
  id: string;
  prerequisites: string[];
};

export type LearningTreeBranch<T extends PrerequisiteNode> = {
  node: T;
  children: LearningTreeBranch<T>[];
  primaryPrerequisiteId: string | null;
};

export function buildLearningTree<T extends PrerequisiteNode>(nodes: T[]) {
  const nodeIds = new Set(nodes.map((node) => node.id));
  const parentById = new Map<string, string>();

  nodes.forEach((node) => {
    const candidates = unique(node.prerequisites).filter(
      (prerequisiteId) => prerequisiteId !== node.id && nodeIds.has(prerequisiteId),
    );
    const parent = candidates.find(
      (candidateId) => !createsCycle(node.id, candidateId, parentById),
    );
    if (parent) parentById.set(node.id, parent);
  });

  const branches = new Map<string, LearningTreeBranch<T>>(
    nodes.map((node) => [
      node.id,
      {
        node,
        children: [],
        primaryPrerequisiteId: parentById.get(node.id) ?? null,
      },
    ]),
  );
  const roots: LearningTreeBranch<T>[] = [];

  nodes.forEach((node) => {
    const branch = branches.get(node.id);
    if (!branch) return;
    const parent = branch.primaryPrerequisiteId ? branches.get(branch.primaryPrerequisiteId) : null;
    if (parent) parent.children.push(branch);
    else roots.push(branch);
  });

  return roots;
}

function createsCycle(childId: string, parentId: string, parentById: Map<string, string>) {
  let cursor: string | undefined = parentId;
  const visited = new Set<string>();
  while (cursor && !visited.has(cursor)) {
    if (cursor === childId) return true;
    visited.add(cursor);
    cursor = parentById.get(cursor);
  }
  return false;
}

function unique(values: string[]) {
  return [...new Set(values)];
}
