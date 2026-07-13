import { fileRelativePath } from "./materialDrop";

const courseMaterialUploadRoot = "uploads";

export function uploadDestination(file: File) {
  return [courseMaterialUploadRoot, fileRelativePath(file)].join("/");
}

export function isSkippableUploadError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  return /A course material file already exists at this path|File type .* is not writable|Hidden workspace paths are not allowed|files are limited to|Empty course material files are not accepted|File contents do not match the requested file type|Declared media type does not match the requested file type/i.test(
    message,
  );
}

export function ignoredUploadNotice(paths: string[]) {
  if (!paths.length) return "";
  const names = paths.map((path) => path.split("/").at(-1) || path);
  const shown = names.slice(0, 5).join(", ");
  const remaining = Math.max(0, names.length - 5);
  return ` Ignored ${names.length} ${names.length === 1 ? "file" : "files"}: ${shown}${remaining ? `, and ${remaining} more` : ""}.`;
}
