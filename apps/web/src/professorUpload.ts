import { fileRelativePath } from "./materialDrop";

export function uploadDestination(basePath: string, file: File, fileCount: number) {
  const target = basePath.trim().replace(/^\/+|\/+$/g, "");
  if (fileCount === 1 && /\.[^/]+$/.test(target)) {
    return target;
  }
  return [target || "uploads", fileRelativePath(file)].join("/");
}

export function isSkippableUploadError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  return /A course material file already exists at this path|File type .* is not writable|Hidden workspace paths are not allowed|files are limited to/i.test(
    message,
  );
}
