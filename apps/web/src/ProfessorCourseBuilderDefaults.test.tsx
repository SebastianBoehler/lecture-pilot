import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import { openProfessorDemo } from "./testLessonActions";

describe("Professor course builder defaults", () => {
  afterEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
  });

  it("shows a backend reachability error when course workspace creation cannot reach the API", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    render(<App />);

    await openProfessorDemo(user);
    await user.type(screen.getByLabelText(/course name/i), "Demo ML Course");
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));

    expect(
      await screen.findByText(
        /cannot reach the local lecturepilot api while creating the course workspace/i,
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/^Failed to fetch$/i)).not.toBeInTheDocument();
  });

  it("sends the selected canvas language while retaining all uploaded materials", async () => {
    const user = userEvent.setup();
    const fetchMock = professorFetchMock();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await openProfessorDemo(user);
    const language = screen.getByLabelText(/course language/i);
    expect(language).toHaveValue("en");
    expect(language).not.toHaveAttribute("aria-describedby");
    await user.selectOptions(language, "de");
    await user.type(screen.getByLabelText(/course name/i), "Bilingual ML Course");
    await user.click(screen.getByRole("button", { name: /create course workspace/i }));

    await waitFor(() => {
      const createCall = fetchMock.mock.calls.find(([url]) =>
        String(url).endsWith("/admin/course-workspaces"),
      );
      expect(createCall).toBeDefined();
      expect(JSON.parse(String(createCall?.[1]?.body))).toMatchObject({ canvas_language: "de" });
    });
  });
});
