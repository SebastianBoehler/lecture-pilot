import { fileRelativePath } from "./materialDrop";
import type { CourseMaterialUploadType } from "./types";
import type { MessageKey } from "./i18nMessages";

type Translate = (key: MessageKey, params?: Record<string, string | number>) => string;

const courseMaterialUploadRoot = "uploads";

export function uploadDestination(file: File) {
  return [courseMaterialUploadRoot, fileRelativePath(file).normalize("NFC")].join("/");
}

export type UploadPreflightExclusion = {
  path: string;
  reason: "duplicate" | "empty" | "oversized" | "unsafe_path" | "unsupported";
};

export function preflightMaterialFiles(
  files: File[],
  supportedUploads: CourseMaterialUploadType[],
) {
  if (!supportedUploads.length) return { accepted: files, excluded: [] };
  const rules = new Map(supportedUploads.map((rule) => [rule.suffix.toLowerCase(), rule]));
  const accepted: File[] = [];
  const excluded: UploadPreflightExclusion[] = [];
  const seen = new Set<string>();
  for (const file of files) {
    const path = uploadDestination(file);
    const parts = path.split("/");
    const suffix = `.${parts.at(-1)?.split(".").at(-1)?.toLowerCase() ?? ""}`;
    const rule = rules.get(suffix);
    let reason: UploadPreflightExclusion["reason"] | null = null;
    if (
      path.startsWith("/") ||
      parts.includes("..") ||
      parts.some((part) => part.startsWith("."))
    ) {
      reason = "unsafe_path";
    } else if (seen.has(path)) {
      reason = "duplicate";
    } else if (!rule) {
      reason = "unsupported";
    } else if (file.size === 0) {
      reason = "empty";
    } else if (file.size > rule.max_bytes) {
      reason = "oversized";
    }
    seen.add(path);
    if (reason) excluded.push({ path, reason });
    else accepted.push(file);
  }
  return { accepted, excluded };
}

export function isSkippableUploadError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  return /A course material file already exists at this path|File type .* is not writable|Hidden workspace paths are not allowed|files are limited to|Empty course material files are not accepted|File contents do not match the requested file type|Declared media type does not match the requested file type/i.test(
    message,
  );
}

export function ignoredUploadNotice(paths: string[], t: Translate) {
  if (!paths.length) return "";
  const names = paths.map((path) => path.split("/").at(-1) || path);
  const remaining = Math.max(0, names.length - 5);
  const shown = names.slice(0, 5).join(", ");
  const listed = remaining
    ? t("builder.status.ignoredMore", { names: shown, count: remaining })
    : shown;
  return ` ${
    names.length === 1
      ? t("builder.status.ignoredOne", { names: listed })
      : t("builder.status.ignoredMany", { count: names.length, names: listed })
  }`;
}
