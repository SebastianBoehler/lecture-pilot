import { fileRelativePath } from "./materialDrop";

export function uploadDestination(basePath: string, file: File, fileCount: number) {
  const target = basePath.trim().replace(/^\/+|\/+$/g, "");
  if (fileCount === 1 && /\.[^/]+$/.test(target)) {
    return target;
  }
  return [target || "uploads", fileRelativePath(file)].join("/");
}
