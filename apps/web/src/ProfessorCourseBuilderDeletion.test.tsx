import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";

describe("Professor course deletion", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("deletes an active course workspace from professor view", async () => {
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

    await user.click(screen.getByRole("button", { name: /preview professor account/i }));
    expect(screen.getByRole("button", { name: /delete course/i })).toBeDisabled();
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    expect(await screen.findByText(/course workspace demo-ml-course ready/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /delete course/i }));

    expect(await screen.findByText(/course workspace demo-ml-course deleted/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/course name/i)).toHaveValue("");
    expect(screen.getByRole("button", { name: /create course workspace/i })).toBeDisabled();
    expect(window.localStorage.getItem("lecturepilot.demo.workspaceCourse")).toBeNull();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/admin/courses/demo-ml-course"),
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
