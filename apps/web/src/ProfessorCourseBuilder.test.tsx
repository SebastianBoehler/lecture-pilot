import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";

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
    expect(screen.queryByRole("heading", { name: /upload and scan materials/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /live course analytics/i })).not.toBeInTheDocument();
    expect(screen.getByLabelText(/course name/i)).toHaveValue("Grundlagen des Maschinellen Lernens");
    expect(screen.getByLabelText(/lecture number/i)).toHaveValue("03");
    expect(screen.getByLabelText(/lecture title/i)).toHaveValue("Bayesian Decision Theory");

    await user.clear(screen.getByLabelText(/course name/i));
    expect(screen.getByRole("button", { name: /create course workspace/i })).toBeDisabled();
    expect(screen.queryByRole("button", { name: /search youtube/i })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /full course/i }));
    expect(screen.getByLabelText(/expected lectures/i)).toHaveValue(null);
    expect(screen.getByRole("button", { name: /create course workspace/i })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: /specific lecture/i }));
    await user.clear(screen.getByLabelText(/lecture title/i));
    await user.type(screen.getByLabelText(/lecture title/i), "Bayesian Decision Theory");
    expect(screen.getByRole("button", { name: /create course workspace/i })).toBeEnabled();
    expect(screen.queryByLabelText(/upload course material/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /04 review/i }));
    expect(screen.getByRole("button", { name: /search youtube/i })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /01 define/i }));

    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    expect(await screen.findByText(/course workspace demo-ml-course\/lecture-03 ready/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /upload and scan materials/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /define course and lecture scope/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /04 review/i }));
    expect(screen.getByRole("button", { name: /search youtube/i })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: /search youtube/i }));
    const candidate = await screen.findByLabelText(/bayesian decision theory/i);
    await user.click(candidate);
    expect(screen.getByRole("button", { name: /include selected videos/i })).toBeDisabled();
    expect(screen.getByText(/generate a canvas draft before attaching/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /02 upload/i }));
    expect(screen.getByText(/upload materials for this lecture for demo ml course/i)).toBeInTheDocument();
    await user.upload(
      screen.getByLabelText(/upload course material/i),
      new File(["# extra note"], "supplement.md", { type: "text/markdown" }),
    );
    await user.click(screen.getByRole("button", { name: /^upload material$/i }));
    expect(await screen.findByText(/uploaded uploads\/supplement\.md/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /generate canvas draft/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /generate draft canvas/i }));
    expect(await screen.findByText(/course-builder agent generated/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /review youtube candidates/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /03 generate/i }));
    expect(await screen.findByText(/2 sections ready for review/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /04 review/i }));

    await user.click(screen.getByRole("button", { name: /include selected videos/i }));

    expect(await screen.findByText(/included 1 approved video/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /publish tutor workspace/i })).toBeInTheDocument();
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
    await user.click(screen.getByRole("button", { name: /03 generate/i }));
    const previewLink = screen.getByRole("link", { name: /preview course workspace/i });
    expect(previewLink).toHaveAttribute("target", "_blank");
    expect(previewLink).toHaveAttribute("href", expect.stringContaining("preview=draft"));
    expect(previewLink).toHaveAttribute("href", expect.stringContaining("courseId=demo-ml-course"));
    expect(await screen.findByText(/2 sections ready for review/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^lecturepilot$/i }));
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
  });

  it("proposes and applies a dated full-course lecture schedule from materials", async () => {
    const user = userEvent.setup();
    const fetchMock = professorFetchMock();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await user.click(screen.getByRole("button", { name: /preview professor account/i }));
    await user.click(screen.getByRole("button", { name: /full course/i }));
    expect(screen.getByLabelText(/expected lectures/i)).toHaveValue(null);
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    await user.click(await screen.findByRole("button", { name: /scan source bundle/i }));

    expect(await screen.findByText(/2 lectures inferred from the source bundle/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue("Lecture 01")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2026-05-13")).toBeInTheDocument();

    await user.clear(screen.getByDisplayValue("Lecture 01"));
    await user.type(screen.getAllByLabelText(/^title$/i)[0], "Course overview");
    await user.click(screen.getByRole("button", { name: /apply lecture schedule/i }));

    expect(await screen.findByText(/lecture schedule applied with 2 dated lectures/i)).toBeInTheDocument();
    const scheduleCall = fetchMock.mock.calls.find((call) => {
      const body = JSON.parse(String(call[1]?.body ?? "{}"));
      return Array.isArray(body.lectures) && body.lectures.length === 2;
    });
    expect(scheduleCall).toBeDefined();
    expect(JSON.parse(String(scheduleCall?.[1]?.body)).lectures[0]).toMatchObject({
      date: "2026-05-06",
      title: "Course overview",
    });
  });

  it("hides the course builder from student accounts", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /preview local demo/i }));

    expect(screen.getByRole("heading", { name: /welcome, local-demo/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^course builder$/i })).not.toBeInTheDocument();
  });
});
