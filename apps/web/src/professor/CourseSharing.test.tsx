import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import { CourseLinkView } from "./CourseLinkView";
import { I18nProvider } from "../i18n/i18n";
import { ProfessorShareCourseDialog } from "./ProfessorShareCourseDialog";
import type { LoginSession, ManagedCourseWorkspaceResult } from "../shared/types";

const session = {
  courses: [{ id: "visible", title: "Visible", professor: "P", term: "WS" }],
  term: "WS 2026",
  username: "student",
} as LoginSession;

const workspace = {
  course: { id: "medvis", title: "Medizinische Visualisierung", professor: "P", term: "WS" },
  lectures: [],
  active_lecture_id: "",
  accessSummary: { default_rule: { audience: "tuebingen_enrolled" }, lectures: [] },
} as unknown as ManagedCourseWorkspaceResult;

function wrap(node: React.ReactNode) {
  return render(
    <I18nProvider locale="en" setLocale={() => {}}>
      {node}
    </I18nProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

it("shares the enrolled-only course link by default and enables joining explicitly", async () => {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === "POST") return Response.json({ path: "/join/medvis/secret-code" });
    return Response.json(null);
  });
  vi.stubGlobal("fetch", fetchMock);
  HTMLDialogElement.prototype.showModal ??= function () {
    this.setAttribute("open", "");
  };
  wrap(<ProfessorShareCourseDialog session={session} workspace={workspace} onClose={vi.fn()} />);

  const link = await screen.findByLabelText("Course link");
  expect(link).toHaveValue(`${window.location.origin}/courses/medvis`);
  expect(screen.getByText(/everyone enrolled in alma or ilias/i)).toBeInTheDocument();
  const toggle = screen.getByRole("checkbox", { name: /allow joining with this link/i });
  await waitFor(() => expect(toggle).toBeEnabled());
  expect(toggle).not.toBeChecked();

  await userEvent.click(toggle);
  await waitFor(() =>
    expect(link).toHaveValue(`${window.location.origin}/join/medvis/secret-code`),
  );
  expect(fetchMock.mock.calls.some(([, init]) => init?.method === "POST")).toBe(true);
});

it("opens accessible courses and explains enrollment otherwise", async () => {
  const open = vi.fn();
  const view = wrap(
    <CourseLinkView courseId="visible" session={session} onOpenCourse={open} onSignIn={vi.fn()} />,
  );
  expect(open).toHaveBeenCalledWith("visible");
  view.unmount();
  wrap(
    <CourseLinkView courseId="other" session={session} onOpenCourse={open} onSignIn={vi.fn()} />,
  );
  expect(screen.getByText(/access follows your alma or ilias enrollment/i)).toBeInTheDocument();
});

it("returns to the shared link after signing in", async () => {
  const signIn = vi.fn();
  wrap(
    <CourseLinkView courseId="medvis" session={null} onOpenCourse={vi.fn()} onSignIn={signIn} />,
  );
  await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
  expect(signIn).toHaveBeenCalledWith("/courses/medvis");
});
