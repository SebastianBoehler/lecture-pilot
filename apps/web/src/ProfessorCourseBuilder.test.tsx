import { render, screen, waitFor } from "@testing-library/react";
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
    expect(screen.queryByRole("heading", { name: /upload materials/i })).not.toBeInTheDocument();
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
    expect(screen.getByRole("button", { name: /create course workspace/i })).toHaveClass("primary-action");
    expect(screen.queryByLabelText(/upload course material/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /03 media/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /04 generate/i })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    expect(await screen.findByText(/course workspace demo-ml-course\/lecture-03 ready/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /upload materials/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /define course and lecture scope/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /03 media/i })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /02 upload/i }));
    expect(screen.getByText(/drop course folder here/i)).toBeInTheDocument();
    expect(screen.getByText(/choose a folder or files/i)).toBeInTheDocument();
    await user.upload(
      screen.getByLabelText(/upload course material/i),
      new File(["# extra note"], "supplement.md", { type: "text/markdown" }),
    );
    expect(screen.getByRole("button", { name: /upload selected materials for this lecture/i })).toHaveClass("primary-action");
    await user.click(screen.getByRole("button", { name: /upload selected materials for this lecture/i }));
    expect(await screen.findByText(/uploaded uploads\/supplement\.md/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /review youtube candidates/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /04 generate/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /search youtube/i })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: /search youtube/i }));
    const candidate = await screen.findByLabelText(/bayesian decision theory/i);
    expect(screen.getByRole("link", { name: /^open$/i })).toHaveAttribute(
      "href",
      "https://www.youtube.com/watch?v=j4yxsEQqPMI",
    );
    expect(screen.getByRole("link", { name: /^open$/i })).toHaveAttribute("target", "_blank");
    await user.click(candidate);
    expect(screen.getByRole("button", { name: /include selected videos/i })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: /include selected videos/i }));
    expect(await screen.findByText(/saved 1 approved video/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /generate canvas draft/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /generate draft canvas/i }));
    expect(await screen.findByText(/course-builder agent generated/i)).toBeInTheDocument();
    expect(screen.getByText(/review needed/i)).toBeInTheDocument();
    expect(screen.getByText(/planner model finished with reason/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /publish tutor workspace/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /04 generate/i }));
    expect(await screen.findByText(/2 sections ready for review/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /05 publish/i }));
    await user.click(screen.getByRole("button", { name: /publish tutor workspace/i }));
    expect(await screen.findByText(/tutor workspace published/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/published lecture workspaces/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /preview/i })).toHaveAttribute("href", expect.stringContaining("lectureId=lecture-03"));
    expect(screen.queryByRole("heading", { name: /live course analytics/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^course performance$/i }));
    expect(await screen.findByRole("heading", { name: /course performance/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /refresh analytics/i }));
    expect(await screen.findByText("Events")).toBeInTheDocument();
    expect(screen.getAllByText("Quiz success").length).toBeGreaterThan(0);
    expect(screen.getAllByText("50%").length).toBeGreaterThan(0);
    expect(screen.getByText(/answer distribution/i)).toBeInTheDocument();
    expect(screen.getByText(/posterior-weighted loss/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^course builder$/i }));
    await user.click(screen.getByRole("button", { name: /04 generate/i }));
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
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/courses/demo-ml-course/media/youtube"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining("/lectures/lecture-03/media/youtube"),
      expect.anything(),
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
    await user.upload(
      await screen.findByLabelText(/upload course material/i),
      new File(["# lecture one"], "Lecture01-eng.tex", { type: "application/x-tex" }),
    );
    await user.click(screen.getByRole("button", { name: /upload selected all course materials/i }));

    expect(await screen.findByText(/2 lectures inferred from the source bundle/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /03 media/i })).toBeDisabled();
    expect(screen.getByDisplayValue("Lecture 01")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2026-05-13")).toBeInTheDocument();

    await user.clear(screen.getByDisplayValue("Lecture 01"));
    await user.type(screen.getAllByLabelText(/^title$/i)[0], "Course overview");
    expect(screen.getByRole("button", { name: /apply lecture schedule/i })).toHaveClass("primary-action");
    await user.click(screen.getByRole("button", { name: /apply lecture schedule/i }));

    expect(await screen.findByText(/lecture schedule applied with 2 dated lectures/i)).toBeInTheDocument();
    const scheduleCall = fetchMock.mock.calls.find((call) => {
      if (typeof call[1]?.body !== "string") return false;
      const body = JSON.parse(call[1].body);
      return Array.isArray(body.lectures) && body.lectures.length === 2;
    });
    expect(scheduleCall).toBeDefined();
    expect(JSON.parse(String(scheduleCall?.[1]?.body)).lectures[0]).toMatchObject({
      date: "2026-05-06",
      title: "Course overview",
    });
    await user.click(screen.getByRole("button", { name: /^course performance$/i }));
    expect(await screen.findByText(/no published course workspace yet/i)).toBeInTheDocument();
  });

  it("restores full-course publish targets after a builder refresh", async () => {
    const user = userEvent.setup();
    const fetchMock = professorFetchMock();
    window.sessionStorage.setItem("lecturepilot.professor-builder.current", JSON.stringify({
      setup: {
        accessPolicy: "tuebingen_enrolled",
        courseTitle: "Demo ML Course",
        lectureTitle: "Bayesian Decision Theory",
        lectureNumber: "03",
        lectureCount: "",
        firstLectureDate: "2026-05-06",
        target: "full-course",
      },
      workspace: { courseId: "demo-ml-course", lectureId: "lecture-01" },
      courseReady: true,
      uploadPath: "uploads",
      bundleReady: true,
      canvasReady: true,
      lectureSchedule: [],
      query: "machine learning lecture",
    }));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await user.click(screen.getByRole("button", { name: /preview professor account/i }));

    expect(await screen.findByText(/0 of 2 lecture workspaces published/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /publish all tutor workspaces/i }));

    expect(await screen.findByText(/2 tutor workspaces published/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/published lecture workspaces/i)).toHaveTextContent("Lecture 01");
    expect(screen.getByLabelText(/published lecture workspaces/i)).toHaveTextContent("Lecture 02");
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/admin/courses/demo-ml-course/lectures/lecture-01/canvas/publish"),
        expect.objectContaining({ method: "POST" }),
      );
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/admin/courses/demo-ml-course/lectures/lecture-02/canvas/publish"),
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("shows a loading state while generating the canvas draft", async () => {
    const user = userEvent.setup();
    const baseFetch = professorFetchMock();
    const draftRequest: { resolve?: () => void } = {};
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url.includes("/canvas/draft") && init?.method === "POST") {
        return new Promise<Response>((resolve) => {
          draftRequest.resolve = () => {
            void Promise.resolve(baseFetch(url, init)).then((response) => resolve(response as Response));
          };
        });
      }
      return baseFetch(url, init);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await user.click(screen.getByRole("button", { name: /preview professor account/i }));
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    await user.upload(
      await screen.findByLabelText(/upload course material/i),
      new File(["# extra note"], "supplement.md", { type: "text/markdown" }),
    );
    await user.click(screen.getByRole("button", { name: /upload selected materials for this lecture/i }));
    await screen.findByRole("heading", { name: /review youtube candidates/i });
    await user.click(screen.getByRole("button", { name: /continue to canvas draft/i }));

    await user.click(screen.getByRole("button", { name: /generate draft canvas/i }));

    expect(screen.getByRole("button", { name: /generating draft canvas/i })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/generating a source-grounded canvas draft/i);
    expect(screen.getByLabelText(/lecture generation progress/i)).toHaveTextContent(/Lecture 03/);
    expect(screen.getByLabelText(/lecture generation progress/i)).toHaveTextContent(/generating/i);

    draftRequest.resolve?.();
    expect(await screen.findByText(/course-builder agent generated/i)).toBeInTheDocument();
  });

  it("hides the course builder from student accounts", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /preview local demo/i }));

    expect(screen.getByRole("heading", { name: /welcome, local-demo/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^course builder$/i })).not.toBeInTheDocument();
  });
});
