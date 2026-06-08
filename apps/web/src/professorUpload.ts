type FileWithRelativePath = File & { webkitRelativePath?: string };

export function uploadDestination(basePath: string, file: File, fileCount: number) {
  const target = basePath.trim().replace(/^\/+|\/+$/g, "");
  if (fileCount === 1 && /\.[^/]+$/.test(target)) {
    return target;
  }
  const relativePath = (file as FileWithRelativePath).webkitRelativePath || file.name;
  return [target || "uploads", relativePath].join("/");
}
