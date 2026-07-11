import { describe, expect, it, vi } from "vitest";

import { installVitePreloadRecovery } from "./vitePreloadRecovery";

describe("installVitePreloadRecovery", () => {
  it("reloads instead of surfacing a stale deployment chunk error", () => {
    const reload = vi.fn();
    const remove = installVitePreloadRecovery(window, reload);
    const event = new Event("vite:preloadError", { cancelable: true });

    window.dispatchEvent(event);

    expect(event.defaultPrevented).toBe(true);
    expect(reload).toHaveBeenCalledOnce();
    remove();
  });
});
