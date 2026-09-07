import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import App from "./App";
import { professorFetchMock } from "./ProfessorCourseBuilder.testFixtures";
import { openProfessorDemo } from "./testLessonActions";

afterEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  vi.unstubAllGlobals();
});

it.each([false, true])("shows automatic source assignment progress (failure: %s)", async (fail) => {
  const user = userEvent.setup();
  const baseFetch = professorFetchMock();
  let finish: (() => void) | undefined;
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    if (url.includes("/source-routing/proposal") && init?.method === "POST") {
      return new Promise<Response>((resolve) => {
        finish = () => {
          if (fail)
            resolve(
              new Response(JSON.stringify({ detail: "Assignment service failed." }), {
                status: 503,
              }),
            );
          else
            void Promise.resolve(baseFetch(url, init)).then((result) =>
              resolve(result as Response),
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
  await user.click(screen.getByRole("button", { name: /create course workspace/i }));
  await user.upload(
    await screen.findByLabelText(/^choose files$/i),
    new File(["# lecture"], "Lecture01-eng.tex", { type: "application/x-tex" }),
  );
  await user.click(screen.getByRole("button", { name: /upload and process materials/i }));
  await screen.findByText(/2 lectures inferred from the source bundle/i);
  await user.click(screen.getByRole("button", { name: /apply lecture schedule/i }));

  expect(await screen.findByText("Preparing source assignments…")).toHaveAttribute(
    "role",
    "status",
  );
  expect(
    screen.queryByRole("button", { name: /retry source assignments/i }),
  ).not.toBeInTheDocument();
  expect(screen.queryByText("0 assigned")).not.toBeInTheDocument();
  expect(screen.queryByText(/review source assignments/i)).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /04 learning plan/i })).toBeDisabled();
  expect(screen.getByRole("button", { name: /refresh workspace state/i })).toBeDisabled();
  expect(
    fetchMock.mock.calls.filter(([url]) => url.includes("/source-routing/proposal")),
  ).toHaveLength(1);

  await act(async () => finish?.());
  if (fail) {
    expect(await screen.findByText("Assignment service failed.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry source assignments/i })).toBeEnabled();
  } else {
    expect(
      await screen.findByRole("button", { name: /accept assignments and continue/i }),
    ).toBeEnabled();
  }
  expect(screen.queryByText("Preparing source assignments…")).not.toBeInTheDocument();
});
