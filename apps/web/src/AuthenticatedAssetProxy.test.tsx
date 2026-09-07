import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { AuthenticatedImage } from "./AuthenticatedAsset";
import type { LoginSession } from "./types";

vi.mock("./api", () => ({
  apiUrl: (path: string) => (/^https?:/.test(path) ? path : `/api${path}`),
}));

const session: LoginSession = {
  access_token: "test-token",
  courses: [],
  roles: ["student"],
  tenant_id: "tenant-tuebingen",
  term: "2026-summer",
  username: "test-student",
};

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it.each(["course-assets", "workspace-assets"])(
  "authenticates %s behind the production API path prefix",
  async (root) => {
    const fetchMock = vi.fn(
      async (_url: unknown, _init?: RequestInit) =>
        new Response(new Blob(["image"], { type: "image/png" })),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:proxy-image");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    render(
      <AuthenticatedImage alt="Protected slide" session={session} src={`/${root}/slide.png`} />,
    );
    await waitFor(() =>
      expect(screen.getByAltText("Protected slide")).toHaveAttribute("src", "blob:proxy-image"),
    );
    expect(fetchMock.mock.calls[0][0]).toBe(`/api/${root}/slide.png`);
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get("Authorization")).toBe(
      "Bearer test-token",
    );
  },
);

it("does not authenticate an external URL with the same protected path", () => {
  const fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
  render(
    <AuthenticatedImage
      alt="External slide"
      session={session}
      src="https://external.example/api/course-assets/slide.png"
    />,
  );
  expect(fetchMock).not.toHaveBeenCalled();
  expect(screen.getByAltText("External slide")).toHaveAttribute(
    "src",
    "https://external.example/api/course-assets/slide.png",
  );
});
