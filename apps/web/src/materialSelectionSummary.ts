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
  if (roots.size === 1 && files.length > 1) {
    return labels.folderSummary(Array.from(roots)[0], files.length);
  }
  return labels.selectedSummary(files.length);
}
