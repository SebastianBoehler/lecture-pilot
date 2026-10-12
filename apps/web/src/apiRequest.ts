import { apiUrl } from "./api";
import { readApiError } from "./apiError";
import { authRequestInit } from "./authz";
import type { LoginSession } from "./types";

/** A non-2xx API response, carrying the backend's detail message and HTTP status. */
export class ApiRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
  }
}

/**
 * Sends an authenticated backend request and returns its JSON body (null when empty).
 * Callers validate or narrow the payload; `fallback` is shown when the backend gives no detail.
 */
export async function apiRequest<T = unknown>(
  session: LoginSession,
  path: string,
  fallback: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(apiUrl(path), authRequestInit(session, init));
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new ApiRequestError(readApiError(payload, fallback), response.status);
  return payload as T;
}
