import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import App from "./App";
import { localProfessorSession } from "./appDefaults";

afterEach(() => {
  window.localStorage.clear();
  window.history.replaceState({}, "", "/");
  vi.unstubAllGlobals();
});

function renderSignedInProfessor(managedCourses: unknown[]) {
  window.localStorage.setItem("lecturepilot.loginSession", JSON.stringify(localProfessorSession));
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) =>
      Response.json(String(input).endsWith("/admin/courses") ? managedCourses : []),
    ),
  );
  render(<App />);
}

it("lands a professor with existing courses on course management", async () => {
  renderSignedInProfessor([
    {
      course: { id: "demo-course", title: "Machine Learning", term: "Sommer 2026" },
      lectures: [],
      active_lecture_id: "",
      published_lecture_ids: [],
      access_summary: {
        course_id: "demo-course",
        default_rule: {
          audience: "tuebingen_enrolled",
          publication_mode: "on_lecture_date",
          publication_at: null,
        },
        lectures: [],
      },
    },
  ]);

  expect(await screen.findByRole("heading", { name: "Manage courses" })).toBeInTheDocument();
  expect(window.location.pathname).toBe("/professor/courses");
  // The managed course list renders from the same response; it must not crash the view.
  expect(await screen.findByText("Machine Learning")).toBeInTheDocument();
});

it("lands a professor without courses in the course builder", async () => {
  renderSignedInProfessor([]);

  await waitFor(() => expect(window.location.pathname).toBe("/professor/courses/new"));
  expect(
    await screen.findByRole("navigation", { name: /course builder progress/i }),
  ).toBeInTheDocument();
});
