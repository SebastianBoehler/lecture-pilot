import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { localProfessorSession } from "./appDefaults";
import { ProfessorCourseManagement } from "./ProfessorCourseManagement";
import { ProfessorCourseUpdate } from "./ProfessorCourseUpdate";

const workspace = {
  course: {
    id: "machine-learning",
    title: "Machine Learning",
    professor: "Prof. Demo",
    term: "Sommer 2026",
  },
  lectures: [
    {
      id: "lecture-01",
      number: "01",
      title: "Introduction",
      date: "2026-05-06",
      attendance: "unknown" as const,
    },
  ],
  active_lecture_id: "lecture-01",
};

describe("Professor course update", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("compares selected files, creates a private draft, and publishes only on confirmation", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/admin/courses") && !init?.method) return json([workspace]);
      if (url.endsWith("/admin/courses/machine-learning/updates") && init?.method === "POST") {
        return json({ course_id: "machine-learning", update_id: "update-1" });
      }
      if (url.includes("/updates/update-1/materials")) {
        return json({ path: "uploads/Lecture02.tex", kind: "latex", size_bytes: 20 });
      }
      if (url.endsWith("/updates/update-1") && !init?.method) {
        return json({
          course_id: "machine-learning",
          update_id: "update-1",
          candidates: [
            {
              candidate_id: "new:2",
              action: "new",
              lecture_id: null,
              number: "02",
              title: "Generalization",
              date: "2026-05-13",
              file_paths: ["uploads/Lecture02.tex"],
            },
          ],
          existing_lectures: [
            {
              lecture_id: "lecture-01",
              number: "01",
              title: "Introduction",
              date: "2026-05-06",
            },
          ],
          unassigned_files: [],
          unchanged_files: 0,
        });
      }
      if (url.endsWith("/updates/update-1/apply")) {
        return json({
          course_id: "machine-learning",
          update_id: "update-1",
          applied_files: 1,
          affected_lecture_ids: ["lecture-02"],
          workspace: {
            ...workspace,
            lectures: [
              ...workspace.lectures,
              {
                id: "lecture-02",
                number: "02",
                title: "Generalization",
                date: "2026-05-13",
                attendance: "unknown",
              },
            ],
          },
        });
      }
      if (url.endsWith("/lectures/lecture-02/canvas/draft")) {
        return json({
          id: "draft",
          course_id: "machine-learning",
          lecture_id: "lecture-02",
          title: "Generalization",
          source_kind: "generated",
          source_ref: "source",
          sections: [],
        });
      }
      if (url.endsWith("/lectures/lecture-02/canvas/publish")) {
        return json({ course_id: "machine-learning", lecture_id: "lecture-02", published: true });
      }
      throw new Error(`Unexpected request: ${init?.method ?? "GET"} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(
      <I18nProvider locale="en" setLocale={() => undefined}>
        <ProfessorCourseManagement
          onCreateCourse={() => undefined}
          onWorkspaceDeleted={() => undefined}
          session={localProfessorSession}
        />
      </I18nProvider>,
    );

    await user.click(await screen.findByRole("button", { name: "Update" }));
    await user.upload(
      screen.getByLabelText("Choose files"),
      new File(["\\title{Generalization}"], "Lecture02.tex", {
        type: "application/x-tex",
      }),
    );
    await user.click(screen.getByRole("button", { name: "Compare materials" }));
    expect(await screen.findByText("Generalization")).toBeInTheDocument();
    expect(screen.getByText("1 file compared")).toBeInTheDocument();
    expect(screen.getByText(/New lecture/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Apply changes and create drafts" }));

    expect(await screen.findByText("Draft ready")).toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/canvas/publish"))).toBe(
      false,
    );
    await user.click(screen.getByRole("button", { name: "Publish 1 ready drafts" }));
    expect(await screen.findByText("Published")).toBeInTheDocument();
  });

  it("keeps a draft ready for retry when publishing fails", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/updates") && init?.method === "POST") {
        return json({ course_id: "machine-learning", update_id: "update-2" });
      }
      if (url.includes("/updates/update-2/materials")) {
        return json({ path: "uploads/Lecture02.tex", kind: "latex", size_bytes: 20 });
      }
      if (url.endsWith("/updates/update-2") && !init?.method) {
        return json({
          course_id: "machine-learning",
          update_id: "update-2",
          candidates: [
            {
              candidate_id: "new:2",
              action: "new",
              lecture_id: null,
              number: "02",
              title: "Generalization",
              date: "2026-05-13",
              file_paths: ["uploads/Lecture02.tex"],
            },
          ],
          existing_lectures: [
            { lecture_id: "lecture-01", number: "01", title: "Introduction", date: "2026-05-06" },
          ],
          unassigned_files: [],
          unchanged_files: 0,
        });
      }
      if (url.endsWith("/updates/update-2/apply")) {
        return json({
          course_id: "machine-learning",
          update_id: "update-2",
          applied_files: 1,
          affected_lecture_ids: ["lecture-02"],
          workspace: {
            ...workspace,
            lectures: [
              ...workspace.lectures,
              {
                id: "lecture-02",
                number: "02",
                title: "Generalization",
                date: "2026-05-13",
                attendance: "unknown",
              },
            ],
          },
        });
      }
      if (url.endsWith("/canvas/draft")) {
        return json({
          id: "draft",
          course_id: "machine-learning",
          lecture_id: "lecture-02",
          title: "Generalization",
          source_kind: "generated",
          source_ref: "source",
          sections: [],
        });
      }
      if (url.endsWith("/canvas/publish")) return json({ detail: "Provider unavailable." }, 502);
      throw new Error(`Unexpected request: ${init?.method ?? "GET"} ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(
      <I18nProvider locale="en" setLocale={() => undefined}>
        <ProfessorCourseUpdate
          onBack={() => undefined}
          onWorkspaceUpdated={() => undefined}
          session={localProfessorSession}
          workspace={workspace}
        />
      </I18nProvider>,
    );
    await user.upload(
      screen.getByLabelText("Choose files"),
      new File(["source"], "Lecture02.tex", { type: "application/x-tex" }),
    );
    await user.click(screen.getByRole("button", { name: "Compare materials" }));
    await user.click(
      await screen.findByRole("button", { name: "Apply changes and create drafts" }),
    );
    await user.click(await screen.findByRole("button", { name: "Publish 1 ready drafts" }));

    expect(await screen.findByText("Provider unavailable.")).toBeInTheDocument();
    expect(screen.getByText("Draft ready")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publish 1 ready drafts" })).toBeEnabled();
  });
});

function json(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
