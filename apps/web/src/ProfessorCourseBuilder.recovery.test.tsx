import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import { openProfessorDemo } from "./testLessonActions";

describe("Professor course builder recovery", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("keeps an applied schedule and retries source routing without another upload", async () => {
    const user = userEvent.setup();
    const baseFetch = professorFetchMock();
    let routingAttempts = 0;
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      if (url.includes("/source-routing/proposal") && init?.method === "POST") {
        routingAttempts += 1;
        if (routingAttempts === 1) {
          return Promise.resolve(
            new Response(
              JSON.stringify({
                detail: "Unknown source path returned: uploads/course/code/PCA-MNIST.ipynb",
              }),
              { status: 503 },
            ),
          );
        }
      }
      return baseFetch(url, init);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await openProfessorDemo(user);
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    await user.upload(
      await screen.findByLabelText(/^choose files$/i),
      new File(["# lecture one"], "Lecture01-eng.tex", {
        type: "application/x-tex",
      }),
    );
    await user.click(screen.getByRole("button", { name: /upload and process materials/i }));
    await screen.findByText(/2 lectures inferred from the source bundle/i);

    await user.click(screen.getByRole("button", { name: /apply lecture schedule/i }));

    expect(await screen.findByText(/unknown source path returned/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^sources$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /03 sources/i })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: /retry source assignments/i }));

    expect(
      await screen.findByRole("button", { name: /accept assignments and continue/i }),
    ).toBeEnabled();
    expect(routingAttempts).toBe(2);
    expect(
      fetchMock.mock.calls.filter(
        ([url, init]) => String(url).includes("/materials") && init?.method === "POST",
      ),
    ).toHaveLength(1);
  });

  it("restores the applied schedule when source routing is still unavailable", async () => {
    const user = userEvent.setup();
    const baseFetch = professorFetchMock();
    window.sessionStorage.setItem(
      "lecturepilot.professor-builder.current",
      JSON.stringify({
        bundleReady: true,
        canvasReady: false,
        courseReady: true,
        lectureSchedule: [
          {
            number: "01",
            title: "Introduction",
            date: "2026-04-14",
            material_path: "Lecture01-eng.tex",
          },
          {
            number: "02",
            title: "Model Selection",
            date: "2026-04-21",
            material_path: "Lecture02-eng.tex",
          },
        ],
        query: "",
        setup: {
          accessPolicy: "tuebingen_enrolled",
          canvasLanguage: "en",
          courseTitle: "Demo ML Course",
          firstLectureDate: "2026-04-14",
          lectureCount: "2",
          lectureNumber: "",
          lectureTitle: "",
          target: "full-course",
        },
        workspace: { courseId: "demo-ml-course", lectureId: "lecture-01" },
      }),
    );
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string, init?: RequestInit) => {
        if (url.endsWith("/source-routing") && init?.method !== "PUT") {
          return Promise.resolve(
            new Response(
              JSON.stringify({ detail: "Source assignment proposal is temporarily unavailable." }),
              { status: 409 },
            ),
          );
        }
        return baseFetch(url, init);
      }),
    );
    render(<App />);

    await openProfessorDemo(user);

    expect(await screen.findByText(/temporarily unavailable/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /^sources$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /03 sources/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /retry source assignments/i })).toBeEnabled();
  });
});
