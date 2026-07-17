export function readApiError(payload: unknown, fallback: string): string {
  if (typeof payload === "string" && payload.trim()) {
    return payload.trim();
  }
  if (!payload || typeof payload !== "object") {
    return fallback;
  }
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail.trim();
  }
  if (!Array.isArray(detail)) {
    return fallback;
  }
  const messages = detail.flatMap((item) => {
    if (!item || typeof item !== "object") {
      return [];
    }
    const { loc, msg } = item as { loc?: unknown; msg?: unknown };
    if (typeof msg !== "string" || !msg.trim()) {
      return [];
    }
    const location = Array.isArray(loc)
      ? loc
          .slice(1)
          .filter(
            (part): part is string | number => typeof part === "string" || typeof part === "number",
          )
          .join(".")
      : "";
    return [location ? `${location}: ${msg.trim()}` : msg.trim()];
  });
  return messages.length ? messages.join("; ") : fallback;
}
