import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("Professor course builder", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("walks through account, course, upload, canvas, and YouTube approval", async () => {
    const user = userEvent.setup();
    const fetchMock = professorFetchMock();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await user.click(screen.getByRole("button", { name: /professor course builder/i }));
    await user.click(screen.getByRole("button", { name: /create professor account/i }));
    expect(screen.getByText(/professor account ready/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    await user.upload(
      screen.getByLabelText(/upload course material/i),
      new File(["# extra note"], "supplement.md", { type: "text/markdown" }),
    );
    await user.click(screen.getByRole("button", { name: /^upload material$/i }));
    expect(await screen.findByText(/uploaded uploads\/supplement\.md/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /scan source bundle/i }));
    expect(await screen.findByText(/3 files indexed/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /generate draft canvas/i }));
    expect(await screen.findByText(/2 sections ready for review/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /search youtube/i }));
    const candidate = await screen.findByLabelText(/bayesian decision theory/i);
    await user.click(candidate);
    await user.click(screen.getByRole("button", { name: /include selected videos/i }));

    expect(await screen.findByText(/included 1 approved video/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/courses/martius-ml/materials"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/media/youtube/search"),
      expect.objectContaining({ headers: expect.objectContaining({ "X-User-Role": "professor" }) }),
    );
  });
});

function professorFetchMock() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (url.includes("/source-bundle")) return json(sourceBundle());
    if (url.includes("/materials")) return json({ path: "uploads/supplement.md", kind: "markdown", size_bytes: 12 });
    if (url.includes("/canvas")) return json(canvasPayload());
    if (url.includes("/media/youtube/search")) return json({ items: [youtubeCandidate()] });
    if (url.includes("/media/youtube")) return json({ block_id: "youtube-j4yxsEQqPMI" });
    throw new Error(`Unexpected fetch: ${url} ${init?.method ?? "GET"}`);
  });
}

function json(payload: unknown) {
  return { ok: true, json: async () => payload };
}

function sourceBundle() {
  return {
    course_id: "martius-ml",
    files: [
      { path: "Lecture03-eng.tex", kind: "latex", size_bytes: 1000 },
      { path: "Ch3/Venn_C-X_1.pdf", kind: "pdf", size_bytes: 2000 },
      { path: "videos/demo.mp4", kind: "video", size_bytes: 3000 },
    ],
    counts_by_kind: { latex: 1, pdf: 1, video: 1 },
  };
}

function canvasPayload() {
  return {
    id: "martius-ml-lecture-03",
    course_id: "martius-ml",
    lecture_id: "lecture-03",
    title: "Bayesian Decision Theory",
    source_kind: "latex",
    source_ref: "Lecture03-eng.tex",
    workspace_path: ".lecturepilot/workspaces/professor-preview/index.md",
    sections: [
      { id: "aim", title: "Decision making", blocks: [] },
      { id: "bayes-formula", title: "Bayes formula", blocks: [] },
    ],
  };
}

function youtubeCandidate() {
  return {
    video_id: "j4yxsEQqPMI",
    title: "Bayesian Decision Theory",
    channel_title: "ML Tübingen",
    description: "Bayes rule and risk.",
    url: "https://www.youtube.com/watch?v=j4yxsEQqPMI",
    duration: { display: "12:15", seconds: 735 },
    score: 9,
    reason: "Matches lecture terms.",
  };
}
