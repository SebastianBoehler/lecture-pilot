import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useVersionUpdateActivity, VersionUpdateBoundary } from "./VersionUpdateBoundary";

afterEach(() => {
  vi.useRealTimers();
  delete (document as unknown as { visibilityState?: DocumentVisibilityState }).visibilityState;
});

describe("VersionUpdateBoundary", () => {
  it("reloads an idle tab when the deployed build changes", async () => {
    const reload = vi.fn();

    render(
      <VersionUpdateBoundary
        buildId="old-build"
        loadBuildId={async () => "new-build"}
        reload={reload}
      >
        <div>App</div>
      </VersionUpdateBoundary>,
    );

    await waitFor(() => expect(reload).toHaveBeenCalledOnce());
  });

  it("defers reload while work is active, then reloads when it finishes", async () => {
    const reload = vi.fn();
    const loadBuildId = vi.fn().mockResolvedValue("new-build");
    const { rerender } = renderBoundary({ active: true, loadBuildId, reload });

    expect(await screen.findByText(/update is ready.*current task finishes/i)).toBeInTheDocument();
    expect(reload).not.toHaveBeenCalled();

    rerender(boundary({ active: false, loadBuildId, reload }));
    await waitFor(() => expect(reload).toHaveBeenCalledOnce());
  });

  it("uses a session guard to avoid an automatic reload loop", async () => {
    const firstReload = vi.fn();
    const loadBuildId = vi.fn().mockResolvedValue("new-build");
    const first = renderBoundary({ active: false, loadBuildId, reload: firstReload });
    await waitFor(() => expect(firstReload).toHaveBeenCalledOnce());
    first.unmount();

    const secondReload = vi.fn();
    renderBoundary({ active: false, loadBuildId, reload: secondReload });

    expect(await screen.findByText(/was updated.*reload the page/i)).toBeInTheDocument();
    expect(secondReload).not.toHaveBeenCalled();
    screen.getByRole("button", { name: "Reload now" }).click();
    expect(secondReload).toHaveBeenCalledOnce();
  });

  it("checks on startup, focus, visible restore, and a visible interval", async () => {
    vi.useFakeTimers();
    setVisibility("visible");
    const loadBuildId = vi.fn().mockResolvedValue("current-build");

    render(
      <VersionUpdateBoundary
        buildId="current-build"
        checkIntervalMs={1_000}
        loadBuildId={loadBuildId}
        reload={vi.fn()}
      >
        <div>App</div>
      </VersionUpdateBoundary>,
    );
    await flushPromises();
    expect(loadBuildId).toHaveBeenCalledTimes(1);

    window.dispatchEvent(new Event("focus"));
    await flushPromises();
    expect(loadBuildId).toHaveBeenCalledTimes(2);

    setVisibility("hidden");
    await act(async () => vi.advanceTimersByTime(1_000));
    expect(loadBuildId).toHaveBeenCalledTimes(2);

    setVisibility("visible");
    document.dispatchEvent(new Event("visibilitychange"));
    await flushPromises();
    expect(loadBuildId).toHaveBeenCalledTimes(3);

    await act(async () => vi.advanceTimersByTime(1_000));
    await flushPromises();
    expect(loadBuildId).toHaveBeenCalledTimes(4);
  });

  it("requests the uncached version manifest", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ buildId: "current-build" }), {
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <VersionUpdateBoundary buildId="current-build" reload={vi.fn()}>
        <div>App</div>
      </VersionUpdateBoundary>,
    );

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith("/version.json", {
        cache: "no-store",
        headers: { Accept: "application/json" },
      }),
    );
  });
});

function BusyActivity({ active }: { active: boolean }) {
  useVersionUpdateActivity(active);
  return null;
}

function boundary({
  active,
  loadBuildId,
  reload,
}: {
  active: boolean;
  loadBuildId: () => Promise<string | null>;
  reload: () => void;
}) {
  return (
    <VersionUpdateBoundary buildId="old-build" loadBuildId={loadBuildId} reload={reload}>
      <BusyActivity active={active} />
    </VersionUpdateBoundary>
  );
}

function renderBoundary(props: Parameters<typeof boundary>[0]) {
  return render(boundary(props));
}

function setVisibility(value: DocumentVisibilityState) {
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value,
  });
}

async function flushPromises() {
  await act(async () => {
    await Promise.resolve();
  });
}
