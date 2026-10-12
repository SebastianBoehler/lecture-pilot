/** Message of a thrown Error, or the given user-facing fallback for anything else. */
export function errorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}
