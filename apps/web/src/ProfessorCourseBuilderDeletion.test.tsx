import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import { openProfessorDemo } from "./testLessonActions";

describe("Professor course deletion", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("deletes a created course from the professor course list", async () => {
    const user = userEvent.setup();
    const fetchMock = professorFetchMock();
    window.localStorage.setItem("lecturepilot.demo.workspaceCourse", JSON.stringify({
      access_policy: "public",
      id: "demo-ml-course",
      title: "Demo ML Course",
      professor: "professor-demo",
      term: "Sommer 2026",
    }));
    vi.stubGlobal("confirm", vi.fn(() => true));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await openProfessorDemo(user);
    expect(screen.getByRole("heading", { name: /^define$/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /created courses/i })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /manage courses/i }));
    expect(await screen.findByRole("heading", { name: /created courses/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /create course/i }));
    expect(await screen.findByRole("heading", { name: /^define$/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /manage courses/i }));
    const deleteButton = await screen.findByRole("button", { name: /delete demo ml course/i });
    expect(deleteButton).toBeEnabled();

    await user.click(deleteButton);

    expect(await screen.findByText(/course workspace demo-ml-course deleted/i)).toBeInTheDocument();
    expect(screen.getByText(/no created course workspaces yet/i)).toBeInTheDocument();
    expect(window.localStorage.getItem("lecturepilot.demo.workspaceCourse")).toBeNull();
    await user.click(screen.getByRole("button", { name: /course performance/i }));
    expect(screen.queryByRole("button", { name: /grundlagen des maschinellen lernens/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/0 published lectures/i)).not.toBeInTheDocument();
    expect(await screen.findByText(/no published course workspace yet/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/courses/demo-ml-course"),
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
