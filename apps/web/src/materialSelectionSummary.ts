import { fileRelativePath } from "./materialDrop";

type MaterialSelectionLabels = {
  folderSummary: (folder: string, count: number) => string;
  noFilesSelected: string;
  selectedSummary: (count: number) => string;
};

const defaultLabels: MaterialSelectionLabels = {
  folderSummary: (folder, count) => `Folder: ${folder} · ${count} files`,
  noFilesSelected: "No files selected",
  selectedSummary: (count) => `${count} selected`,
};

export function materialSelectionSummary(
  files: File[],
  labels: MaterialSelectionLabels = defaultLabels,
) {
  if (!files.length) return labels.noFilesSelected;
  const roots = new Set(files.map((file) => fileRelativePath(file).split("/")[0]).filter(Boolean));
  const kinds = kindCounts(files);
  const kindText = Object.entries(kinds)
    .map(([kind, count]) => `${count} ${kind}`)
    .join(" · ");
  if (roots.size === 1 && files.length > 1) {
    return `${labels.folderSummary(Array.from(roots)[0], files.length)}${kindText ? ` · ${kindText}` : ""}`;
  }
  return `${labels.selectedSummary(files.length)}${kindText ? ` · ${kindText}` : ""}`;
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
