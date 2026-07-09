import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthenticatedImage } from "./AuthenticatedAsset";
import type { LoginSession } from "./types";

const session: LoginSession = {
  access_token: "signed-token",
  courses: [],
  roles: ["student"],
  tenant_id: "tenant-tuebingen",
  term: "2026-summer",
  username: "student01",
};

describe("AuthenticatedImage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("fetches LecturePilot assets with session auth and renders a blob URL", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(new Blob(["png"], { type: "image/png" })),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:lecturepilot-asset");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);

    render(
      <AuthenticatedImage
        alt="Risk diagram"
        session={session}
        src="/course-assets/demo-course/lecture-01/figures/risk.png"
      />,
    );

    const image = await screen.findByAltText("Risk diagram");
    expect(image).toHaveAttribute("src", "blob:lecturepilot-asset");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/course-assets/demo-course/lecture-01/figures/risk.png",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get("authorization")).toBe(
      "Bearer signed-token",
    );
  });

  it("does not send auth headers to external image URLs", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AuthenticatedImage
        alt="External diagram"
        session={session}
        src="https://example.edu/assets/risk.png"
      />,
    );

    const image = screen.getByAltText("External diagram");
    expect(image).toHaveAttribute("src", "https://example.edu/assets/risk.png");
    await waitFor(() => expect(fetchMock).not.toHaveBeenCalled());
  });
});
