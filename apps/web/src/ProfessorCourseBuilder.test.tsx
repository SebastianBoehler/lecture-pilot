import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";

describe("Professor course builder", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("walks through course upload, canvas, and YouTube approval as a professor account", async () => {
    const user = userEvent.setup();
    const fetchMock = professorFetchMock();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await user.click(screen.getByRole("button", { name: /preview professor account/i }));
    expect(screen.queryByRole("heading", { name: /professor sign up/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /create professor account/i })).not.toBeInTheDocument();
    expect(screen.getByText(/signed in as professor-demo/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /define course and lecture scope/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /live course analytics/i })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/course name/i)).toHaveValue("Grundlagen des Maschinellen Lernens");
    expect(screen.getByLabelText(/lecture number/i)).toHaveValue("03");
    expect(screen.getByLabelText(/lecture title/i)).toHaveValue("Bayesian Decision Theory");

    await user.clear(screen.getByLabelText(/course name/i));
    expect(screen.getByRole("button", { name: /create course workspace/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /search youtube/i })).toBeDisabled();
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /full course/i }));
    expect(screen.getByLabelText(/number of lectures/i)).toHaveValue(14);
    await user.clear(screen.getByLabelText(/number of lectures/i));
    expect(screen.getByRole("button", { name: /create course workspace/i })).toBeDisabled();
    await user.type(screen.getByLabelText(/number of lectures/i), "12");
    await user.click(screen.getByRole("button", { name: /specific lecture/i }));
    await user.clear(screen.getByLabelText(/lecture title/i));
    await user.type(screen.getByLabelText(/lecture title/i), "Bayesian Decision Theory");
    expect(screen.getByRole("button", { name: /create course workspace/i })).toBeEnabled();
    expect(screen.getByLabelText(/upload course material/i)).toBeDisabled();
    expect(screen.getByRole("button", { name: /search youtube/i })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    expect(await screen.findByText(/course workspace demo-ml-course\/lecture-03 ready/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /search youtube/i })).toBeEnabled();
    expect(screen.getByText(/upload materials for this lecture for demo ml course/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /search youtube/i }));
    const candidate = await screen.findByLabelText(/bayesian decision theory/i);
    await user.click(candidate);
    expect(screen.getByRole("button", { name: /include selected videos/i })).toBeDisabled();
    expect(screen.getByText(/generate a canvas draft before attaching/i)).toBeInTheDocument();

    await user.upload(
      screen.getByLabelText(/upload course material/i),
      new File(["# extra note"], "supplement.md", { type: "text/markdown" }),
    );
    await user.click(screen.getByRole("button", { name: /^upload material$/i }));
    expect(await screen.findByText(/uploaded uploads\/supplement\.md/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /scan source bundle/i }));
    expect(await screen.findByText(/3 files indexed/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /generate draft canvas/i }));
    expect(await screen.findByText(/course-builder agent generated/i)).toBeInTheDocument();
    expect(await screen.findByText(/2 sections ready for review/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /include selected videos/i }));

    expect(await screen.findByText(/included 1 approved video/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /publish tutor workspace/i }));
    expect(await screen.findByText(/tutor workspace published/i)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /live course analytics/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^course performance$/i }));
    expect(await screen.findByRole("heading", { name: /course performance/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /refresh analytics/i }));
    expect(await screen.findByText("Events")).toBeInTheDocument();
    expect(screen.getByText("Quiz success")).toBeInTheDocument();
    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.getByText(/answer distribution/i)).toBeInTheDocument();
    expect(screen.getByText(/posterior-weighted loss/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^course builder$/i }));
    await user.click(screen.getByRole("button", { name: /preview course workspace/i }));
    expect(
      await screen.findByRole("heading", { name: /^bayesian decision theory$/i, level: 1 }),
    ).toBeInTheDocument();
    const lessonToolbar = screen.getByText("Draft").closest(".lesson-toolbar") as HTMLElement;
    expect(within(lessonToolbar).getByRole("button", { name: /course builder/i })).toBeInTheDocument();
    await user.click(within(lessonToolbar).getByRole("button", { name: /course builder/i }));
    expect(await screen.findByText(/2 sections ready for review/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^back$/i }));
    expect(screen.getByText(/ai tutor available/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^course builder$/i }));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/courses/demo-ml-course/materials"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/courses/demo-ml-course/lectures/lecture-03/canvas/draft"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/courses/demo-ml-course/media/youtube/search"),
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-User-Id": "professor-demo",
          "X-User-Role": "professor",
        }),
      }),
    );
    await user.click(screen.getByRole("button", { name: /reset flow/i }));
    expect(await screen.findByText(/professor flow reset/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/courses/demo-ml-course/media/youtube"),
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("hides the course builder from student accounts", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /preview local demo/i }));

    expect(screen.getByRole("heading", { name: /welcome, local-demo/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^course builder$/i })).not.toBeInTheDocument();
  });
});

function professorFetchMock() {
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith("/admin/course-workspaces")) return json(courseWorkspacePayload(init));
    if (url.includes("/source-bundle")) return json(sourceBundle());
    if (url.includes("/materials")) return json({ path: "uploads/supplement.md", kind: "markdown", size_bytes: 12 });
    if (url.includes("/analytics")) return json(analyticsPayload());
    if (url.includes("/canvas/draft")) return json(canvasPayload());
    if (url.includes("/canvas")) return json(canvasPayload());
    if (url.includes("/media/youtube/search")) return json({ items: [youtubeCandidate()] });
    if (url.includes("/media/youtube") && init?.method === "DELETE") return json({ deleted: 1 });
    if (url.includes("/media/youtube")) return json({ block_id: "youtube-j4yxsEQqPMI" });
    throw new Error(`Unexpected fetch: ${url} ${init?.method ?? "GET"}`);
  });
}

function json(payload: unknown) {
  return { ok: true, json: async () => payload };
}

function sourceBundle() {
  return {
    course_id: "demo-ml-course",
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
    id: "demo-ml-course-lecture-03",
    course_id: "demo-ml-course",
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

function analyticsPayload() {
  return {
    course_id: "demo-ml-course",
    lecture_id: "lecture-03",
    total_events: 3,
    quizzes: [
      {
        component_id: "risk-check",
        component_type: "single_choice_quiz",
        title: "Risk threshold check",
        question: "Which action minimizes expected risk?",
        total_attempts: 2,
        unique_learners: 2,
        correct_attempts: 1,
        correct_rate: 0.5,
        attendance_split: { absent: 1, present: 1 },
        options: [
          { option_index: 0, option_id: "prior-only", text: "Use the largest class prior.", selections: 1, correct: false },
          { option_index: 1, option_id: "posterior-loss", text: "Use posterior-weighted loss.", selections: 1, correct: true },
        ],
      },
    ],
    gates: [
      {
        gate_id: "risk-gate",
        total_events: 1,
        unique_learners: 1,
        status_counts: { passed: 1 },
        attendance_split: { present: 1 },
      },
    ],
  };
}

function courseWorkspacePayload(init?: RequestInit) {
  const body = JSON.parse(String(init?.body ?? "{}"));
  return {
    course: {
      id: "demo-ml-course",
      title: body.course_title,
      professor: "professor-demo",
      term: "Sommer 2026",
    },
    lectures: [
      {
        id: "lecture-03",
        course_id: "demo-ml-course",
        title: body.lecture_title,
        date: "2026-06-11",
      },
    ],
    active_lecture_id: "lecture-03",
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
