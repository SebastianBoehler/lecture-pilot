import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import { openProfessorDemo } from "./testLessonActions";

describe("Professor course builder", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("walks through course upload, canvas, and YouTube approval as a professor account", async () => {
    const user = userEvent.setup();
    const fetchMock = professorFetchMock();
    window.localStorage.setItem(
      "lecturepilot.demo.workspaceCourse",
      JSON.stringify({
        access_policy: "public",
        id: "martius-ml",
        title: "Grundlagen des Maschinellen Lernens",
        professor: "Prof. Georg Martius",
        term: "Sommer 2026",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await openProfessorDemo(user);
    expect(screen.queryByRole("heading", { name: /professor sign up/i })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /create professor account/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open profile/i })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /define course and lecture scope/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/course builder\s*·/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /upload materials/i })).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /live course analytics/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByLabelText(/course name/i)).toHaveValue("");
    expect(screen.queryByLabelText(/lecture number/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /full course/i })).toHaveClass("is-active");

    expect(screen.getByRole("button", { name: /create course workspace/i })).toBeDisabled();
    expect(screen.queryByRole("button", { name: /search youtube/i })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    expect(screen.getByLabelText(/expected lectures/i)).toHaveValue(null);
    expect(screen.getByRole("button", { name: /create course workspace/i })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: /specific lecture/i }));
    await user.type(screen.getByLabelText(/lecture number/i), "03");
    await user.clear(screen.getByLabelText(/lecture title/i));
    await user.type(screen.getByLabelText(/lecture title/i), "Bayesian Decision Theory");
    expect(screen.getByRole("button", { name: /create course workspace/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /create course workspace/i })).toHaveClass(
      "primary-action",
    );
    expect(screen.queryByLabelText(/upload course material/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /03 media/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /04 generate/i })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    expect(
      await screen.findByText(/course workspace demo-ml-course\/lecture-03 ready/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /upload materials/i })).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: /define course and lecture scope/i }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /03 media/i })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /^lecturepilot$/i }));
    expect(await screen.findByRole("heading", { name: /upload materials/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /course workspaces/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^course builder$/i }));
    expect(await screen.findByRole("heading", { name: /upload materials/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /02 upload/i }));
    expect(screen.getByText(/drop a folder or files here/i)).toBeInTheDocument();
    expect(screen.getByText(/choose a folder or files/i)).toBeInTheDocument();
    expect(screen.getByText(/^choose files$/i)).toBeInTheDocument();
    expect(screen.getByText(/^choose folder$/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/workspace folder/i)).not.toBeInTheDocument();
    expect(
      screen.getByText(/build and system files are ignored automatically/i),
    ).toBeInTheDocument();
    await user.upload(
      screen.getByLabelText(/^choose files$/i),
      new File(["# extra note"], "supplement.md", { type: "text/markdown" }),
    );
    expect(screen.getByRole("button", { name: /upload and process materials/i })).toHaveClass(
      "primary-action",
    );
    expect(screen.queryByRole("button", { name: /scan uploaded bundle/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /upload and process materials/i }));
    expect(await screen.findByText(/uploaded uploads\/supplement\.md/i)).toBeInTheDocument();
    const materialUploadCall = fetchMock.mock.calls.find(
      ([url, init]) => String(url).includes("/materials") && init?.method === "POST",
    );
    expect(materialUploadCall?.[1]?.body).toBeInstanceOf(FormData);
    expect((materialUploadCall?.[1]?.body as FormData).get("path")).toBe("uploads/supplement.md");
    expect((materialUploadCall?.[1]?.body as FormData).get("refresh_index")).toBe("false");
    expect(screen.getByRole("heading", { name: /review youtube candidates/i })).toBeInTheDocument();
    expect(screen.getByText(/videos are saved directly for lecture 03/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /04 generate/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /search youtube/i })).toBeEnabled();
    const candidate = await screen.findByLabelText(/bayesian decision theory/i);
    expect(screen.getByRole("button", { name: /refresh suggested videos/i })).toBeEnabled();
    expect(
      screen.getByRole("img", { name: /thumbnail for bayesian decision theory/i }),
    ).toHaveAttribute("src", "https://i.ytimg.com/vi/j4yxsEQqPMI/hqdefault.jpg");
    expect(screen.getByRole("link", { name: /^open$/i })).toHaveAttribute(
      "href",
      "https://www.youtube.com/watch?v=j4yxsEQqPMI",
    );
    expect(screen.getByRole("link", { name: /^open$/i })).toHaveAttribute("target", "_blank");
    await user.click(candidate);
    expect(await screen.findByText(/saved 1 approved video for lecture 03/i)).toBeInTheDocument();
    expect(candidate).toBeChecked();
    expect(
      screen.queryByRole("button", { name: /include selected videos/i }),
    ).not.toBeInTheDocument();

    await user.click(candidate);
    expect(await screen.findByText(/removed video from lecture 03/i)).toBeInTheDocument();
    expect(candidate).not.toBeChecked();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining(
        "/admin/courses/demo-ml-course/lectures/lecture-03/media/youtube/j4yxsEQqPMI",
      ),
      expect.objectContaining({ method: "DELETE" }),
    );

    await user.click(candidate);
    expect(await screen.findByText(/saved 1 approved video for lecture 03/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /continue to canvas draft/i }));
    expect(screen.getByRole("heading", { name: /generate canvas draft/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /generate draft canvas/i }));
    expect(await screen.findByText(/course-builder agent generated/i)).toBeInTheDocument();
    expect(screen.getByText(/review needed/i)).toBeInTheDocument();
    expect(screen.getByText(/planner model finished with reason/i)).toBeInTheDocument();
    expect(await screen.findByText(/2 sections ready for review/i)).toBeInTheDocument();
    const draftPreview = screen.getByRole("link", { name: /preview course workspace/i });
    expect(draftPreview).toHaveAttribute(
      "href",
      expect.stringContaining("/professor/courses/demo-ml-course/lectures/lecture-03/draft"),
    );
    expect(screen.getByRole("button", { name: /05 publish/i })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /continue to publishing/i }));
    expect(screen.getByRole("heading", { name: /publish tutor workspace/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /publish tutor workspace/i }));
    expect(await screen.findByText(/tutor workspace published/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/published lecture workspaces/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /preview/i })).toHaveAttribute(
      "href",
      expect.stringContaining("/professor/courses/demo-ml-course/lectures/lecture-03/draft"),
    );
    expect(
      screen.queryByRole("heading", { name: /live course analytics/i }),
    ).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^course performance$/i }));
    expect(await screen.findByRole("heading", { name: /course performance/i })).toBeInTheDocument();
    expect(
      screen.queryByRole("navigation", { name: /performance course scope/i }),
    ).not.toBeInTheDocument();
    expect(await screen.findByText(/^demo ml course$/i)).toBeInTheDocument();
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
    expect(previewLink).toHaveAttribute(
      "href",
      expect.stringContaining("/professor/courses/demo-ml-course/lectures/lecture-03/draft"),
    );
    expect(await screen.findByText(/2 sections ready for review/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^lecturepilot$/i }));
    expect(await screen.findByRole("heading", { name: /^generate$/i })).toBeInTheDocument();
    expect(screen.queryByText(/ai tutor available/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^course builder$/i }));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/courses/demo-ml-course/materials"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/courses/demo-ml-course/lectures/lecture-03/canvas/draft"),
      expect.objectContaining({ method: "POST" }),
    );
    const youtubeSearchCall = fetchMock.mock.calls.find(([url]) =>
      String(url).includes("/admin/courses/demo-ml-course/media/youtube/search"),
    );
    const youtubeSearchHeaders = new Headers(youtubeSearchCall?.[1]?.headers);
    expect(youtubeSearchHeaders.get("x-user-id")).toBe("professor-demo");
    expect(youtubeSearchHeaders.get("x-user-role")).toBe("professor");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/courses/demo-ml-course/lectures/lecture-03/media/youtube"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(
      fetchMock.mock.calls.some(
        ([url, init]) =>
          String(url).endsWith("/admin/courses/demo-ml-course/media/youtube") &&
          init?.method === "POST",
      ),
    ).toBe(false);
  }, 15_000);

  it("proposes and applies a dated full-course lecture schedule from materials", async () => {
    const user = userEvent.setup();
    const fetchMock = professorFetchMock();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await openProfessorDemo(user);
    expect(screen.getByLabelText(/course name/i)).toHaveValue("");
    expect(screen.getByRole("button", { name: /full course/i })).toHaveClass("is-active");
    expect(screen.getByLabelText(/expected lectures/i)).toHaveValue(null);
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    await user.upload(
      await screen.findByLabelText(/^choose files$/i),
      new File(["# lecture one"], "Lecture01-eng.tex", { type: "application/x-tex" }),
    );
    await user.click(screen.getByRole("button", { name: /upload and process materials/i }));

    expect(
      await screen.findByText(/2 lectures inferred from the source bundle/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /03 media/i })).toBeDisabled();
    expect(screen.getByDisplayValue("Lecture 01")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2026-05-13")).toBeInTheDocument();
    expect(screen.getByText("Lecture01-eng.tex")).toHaveAttribute("title", "Lecture01-eng.tex");

    await user.click(screen.getByRole("button", { name: /remove lecture 02 from schedule/i }));
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining("Lecture 02"));
    expect(screen.queryByDisplayValue("2026-05-13")).not.toBeInTheDocument();
    expect(screen.getByText(/1 lecture inferred from the source bundle/i)).toBeInTheDocument();

    await user.clear(screen.getByDisplayValue("Lecture 01"));
    await user.type(screen.getAllByLabelText(/^title$/i)[0], "Course overview");
    expect(screen.getByRole("button", { name: /apply lecture schedule/i })).toHaveClass(
      "primary-action",
    );
    await user.click(screen.getByRole("button", { name: /apply lecture schedule/i }));

    expect(
      await screen.findByText(/lecture schedule applied with 1 dated lectures/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/videos are saved directly for lecture 01/i)).toBeInTheDocument();
    const scheduleCall = fetchMock.mock.calls.find((call) => {
      if (typeof call[1]?.body !== "string") return false;
      const body = JSON.parse(call[1].body);
      return Array.isArray(body.lectures) && body.lectures.length === 1;
    });
    expect(scheduleCall).toBeDefined();
    const scheduleRequest = JSON.parse(String(scheduleCall?.[1]?.body));
    expect(scheduleRequest).toMatchObject({ replace_lectures: true });
    expect(scheduleRequest.lectures[0]).toMatchObject({
      date: "2026-05-06",
      title: "Course overview",
    });
    await user.click(screen.getByRole("button", { name: /^course performance$/i }));
    expect(await screen.findByText(/no published course workspace yet/i)).toBeInTheDocument();
  });

  it("restores full-course publish targets after a builder refresh", async () => {
    const user = userEvent.setup();
    const fetchMock = professorFetchMock();
    window.sessionStorage.setItem(
      "lecturepilot.professor-builder.current",
      JSON.stringify({
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
        bundleReady: true,
        canvasReady: true,
        lectureSchedule: [],
        query: "machine learning lecture",
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await openProfessorDemo(user);

    expect(await screen.findByText(/2 lecture canvases ready to review/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /05 publish/i })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /continue to publishing/i }));
    expect(await screen.findByText(/0 of 2 lecture workspaces published/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /publish all tutor workspaces/i }));

    expect(await screen.findByText(/2 tutor workspaces published/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/published lecture workspaces/i)).toHaveTextContent("Lecture 01");
    expect(screen.getByLabelText(/published lecture workspaces/i)).toHaveTextContent("Lecture 02");
    await user.click(screen.getByRole("button", { name: /^course performance$/i }));
    expect(await screen.findByText(/2 published lectures/i)).toBeInTheDocument();
    expect(screen.queryByText(/no published course workspace yet/i)).not.toBeInTheDocument();
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
            void Promise.resolve(baseFetch(url, init)).then((response) =>
              resolve(response as Response),
            );
          };
        });
      }
      return baseFetch(url, init);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await openProfessorDemo(user);
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /specific lecture/i }));
    await user.type(screen.getByLabelText(/lecture number/i), "03");
    await user.type(screen.getByLabelText(/lecture title/i), "Bayesian Decision Theory");
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    await user.upload(
      await screen.findByLabelText(/^choose files$/i, {}, { timeout: 3_000 }),
      new File(["# extra note"], "supplement.md", { type: "text/markdown" }),
    );
    await user.click(screen.getByRole("button", { name: /upload and process materials/i }));
    await screen.findByRole("heading", { name: /review youtube candidates/i });
    await user.click(screen.getByRole("button", { name: /continue to canvas draft/i }));

    await user.click(screen.getByRole("button", { name: /generate draft canvas/i }));

    expect(screen.getByRole("button", { name: /generating draft canvas/i })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(
      /generating a source-grounded canvas draft/i,
    );
    expect(screen.getByLabelText(/lecture generation progress/i)).toHaveTextContent(/Lecture 03/);
    expect(screen.getByLabelText(/lecture generation progress/i)).toHaveTextContent(/generating/i);

    draftRequest.resolve?.();
    expect(await screen.findByText(/course-builder agent generated/i)).toBeInTheDocument();
  });

  it("hides the course builder from student accounts", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("button", { name: /preview local demo/i }));

    expect(screen.getByRole("heading", { name: /welcome/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^course builder$/i })).not.toBeInTheDocument();
  });
});
