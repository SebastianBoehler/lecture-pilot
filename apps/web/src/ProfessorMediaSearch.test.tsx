import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import { openProfessorDemo } from "./testLessonActions";

describe("Professor lecture media search", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("updates suggested and manual searches with the selected lecture", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", professorFetchMock());
    render(<App />);

    await openProfessorDemo(user);
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));
    await user.upload(
      await screen.findByLabelText(/^choose files$/i),
      new File(["# lecture one"], "Lecture01-eng.tex", { type: "application/x-tex" }),
    );
    await user.click(screen.getByRole("button", { name: /upload and process materials/i }));
    await user.click(await screen.findByRole("button", { name: /apply lecture schedule/i }));

    const target = screen.getByLabelText(/choose videos for/i);
    const suggestions = screen.getByRole("region", { name: /suggested searches/i });
    expect(target).toHaveValue("lecture-01");
    expect(within(suggestions).getAllByText(/Lecture 01/).length).toBeGreaterThan(0);
    const firstLectureVideo = await screen.findByLabelText(/bayesian decision theory/i);
    await user.click(firstLectureVideo);
    expect(await screen.findByText(/saved 1 approved video for lecture 01/i)).toBeInTheDocument();

    await user.selectOptions(target, "lecture-02");

    await waitFor(() => {
      expect(within(suggestions).getAllByText(/Lecture 02/).length).toBeGreaterThan(0);
      expect((screen.getByLabelText(/search query/i) as HTMLInputElement).value).toContain(
        "Lecture 02",
      );
    });
    expect(within(suggestions).queryAllByText(/Lecture 01/)).toHaveLength(0);
    expect(await screen.findByLabelText(/bayesian decision theory/i)).not.toBeChecked();

    await user.selectOptions(target, "lecture-01");
    await waitFor(() => {
      expect(screen.getByLabelText(/bayesian decision theory/i)).toBeChecked();
    });
  });
});
