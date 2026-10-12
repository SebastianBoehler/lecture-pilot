const LOCAL_API_BASE_URL = "http://127.0.0.1:8000";

export function resolveApiBaseUrl(production: boolean, configured?: string): string {
  if (production) {
    return "/api";
  }
  return configured?.trim() || LOCAL_API_BASE_URL;
}
