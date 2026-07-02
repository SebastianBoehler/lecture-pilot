import { fileRelativePath } from "./materialDrop";

export function materialSelectionSummary(files: File[]) {
  if (!files.length) return "No files selected";
  const roots = new Set(files.map((file) => fileRelativePath(file).split("/")[0]).filter(Boolean));
  const kinds = kindCounts(files);
  const kindText = Object.entries(kinds)
    .map(([kind, count]) => `${count} ${kind}`)
    .join(" · ");
  if (roots.size === 1 && files.length > 1) {
    return `Folder: ${Array.from(roots)[0]} · ${files.length} files${kindText ? ` · ${kindText}` : ""}`;
  }
  return `${files.length} selected${kindText ? ` · ${kindText}` : ""}`;
}

function kindCounts(files: File[]) {
  return files.reduce<Record<string, number>>((counts, file) => {
    const kind = fileKind(fileRelativePath(file));
    counts[kind] = (counts[kind] ?? 0) + 1;
    return counts;
  }, {});
}

function fileKind(path: string) {
  const suffix = path.split(".").pop()?.toLowerCase();
  if (suffix === "tex") return "LaTeX";
  if (suffix === "pdf") return "PDF";
  if (suffix === "md") return "Markdown";
  if (suffix === "txt") return "text";
  return suffix ? suffix.toUpperCase() : "files";
}
