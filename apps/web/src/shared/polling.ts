/** One shared way to poll server state without hammering a small API host. */

export type PollStep<T> = { done: true; value: T } | { done: false; retryAfterMs?: number };

export type PollOptions<T> = {
  /** One status request. Return `done: false` to keep waiting (optionally honoring Retry-After). */
  poll: (signal: AbortSignal | undefined) => Promise<PollStep<T>>;
  initialDelayMs: number;
  maxDelayMs: number;
  /** Overall wall-clock budget; at least one request runs after a hidden-tab pause. */
  timeoutMs: number;
  backoffFactor?: number;
  signal?: AbortSignal;
};

export class PollTimeoutError extends Error {
  constructor() {
    super("Polling deadline reached.");
    this.name = "PollTimeoutError";
  }
}

/**
 * Waits before every request, grows the delay exponentially up to `maxDelayMs`, pauses while the
 * document is hidden, honors a server Retry-After, and rejects with the abort reason on abort.
 */
export async function pollUntil<T>({
  poll,
  initialDelayMs,
  maxDelayMs,
  timeoutMs,
  backoffFactor = 1.5,
  signal,
}: PollOptions<T>): Promise<T> {
  const deadline = Date.now() + timeoutMs;
  let delayMs = initialDelayMs;
  while (true) {
    await abortableDelay(delayMs, signal);
    await whileHidden(signal);
    const step = await poll(signal);
    if (step.done) return step.value;
    if (Date.now() >= deadline) throw new PollTimeoutError();
    const backoffMs = Math.min(maxDelayMs, delayMs * backoffFactor);
    delayMs = Math.max(backoffMs, step.retryAfterMs ?? 0);
  }
}

/** Parses Retry-After (seconds or HTTP date) on rate-limited or unavailable responses. */
export function retryAfterMs(response: Response): number | undefined {
  if (response.status !== 429 && response.status !== 503) return undefined;
  const header = response.headers.get("Retry-After")?.trim();
  if (!header) return undefined;
  const seconds = Number(header);
  if (Number.isFinite(seconds)) return Math.max(0, seconds * 1000);
  const date = Date.parse(header);
  return Number.isNaN(date) ? undefined : Math.max(0, date - Date.now());
}

/** True for responses a poller should wait out instead of treating as failures. */
export function isTransientPollResponse(response: Response) {
  return response.status === 429 || response.status === 503;
}

function abortableDelay(ms: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    signal?.throwIfAborted();
    const timer = window.setTimeout(() => {
      signal?.removeEventListener("abort", stop);
      resolve();
    }, ms);
    function stop() {
      window.clearTimeout(timer);
      reject(signal?.reason);
    }
    signal?.addEventListener("abort", stop, { once: true });
  });
}

function whileHidden(signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    signal?.throwIfAborted();
    if (document.visibilityState !== "hidden") {
      resolve();
      return;
    }
    function visible() {
      if (document.visibilityState === "hidden") return;
      cleanup();
      resolve();
    }
    function stop() {
      cleanup();
      reject(signal?.reason);
    }
    function cleanup() {
      document.removeEventListener("visibilitychange", visible);
      signal?.removeEventListener("abort", stop);
    }
    document.addEventListener("visibilitychange", visible);
    signal?.addEventListener("abort", stop, { once: true });
  });
}
