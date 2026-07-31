import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PracticeExamSetup } from "./PracticeExamSetup";
import type { PpiExamSource } from "./practiceExamTypes";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LoginSession, UniversityCourse } from "./types";

describe("PracticeExamSetup", () => {
  it("blocks generation and hides other courses while one PPI source imports", async () => {
    let finishImport: ((response: Response) => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/catalog")) return json(catalog);
        if (url.endsWith("/imports")) {
          return new Promise<Response>((resolve) => {
            finishImport = resolve;
          });
        }
        return json([]);
      }),
    );
    const user = userEvent.setup();
    renderSetup();

    await user.click(screen.getByRole("button", { name: "Import from PPI" }));
    await user.type(screen.getByLabelText("PPI username"), "student");
    await user.type(screen.getByLabelText("PPI password"), "secret");
    await user.click(screen.getByRole("button", { name: "Load PPI courses" }));
    await user.click(
      await screen.findByRole("button", { name: "Import: Natural Language Processing" }),
    );

    expect(screen.getByRole("button", { name: "Importing PPI source…" })).toBeDisabled();
    expect(screen.getByText("Importing…").parentElement).toHaveTextContent(
      "Natural Language Processing · 5 protocols",
    );
    expect(screen.queryByText("Probabilistic Machine Learning")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("PPI password")).not.toBeInTheDocument();

    finishImport?.(jsonResponse({ source, reused: false, token_spent: false }));
    await waitFor(() => expect(screen.getByText("Ready for exam generation")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Generate 25-question exam" })).toBeEnabled();
    expect(screen.queryByText("Saved privately")).not.toBeInTheDocument();
  });
});

function renderSetup() {
  return renderWithI18n(
    <PracticeExamSetup
      course={course}
      error={null}
      generating={false}
      session={session}
      sources={[]}
      onClose={vi.fn()}
      onGenerate={vi.fn()}
      onSourceImported={vi.fn()}
    />,
  );
}

const course: UniversityCourse = {
  id: "course-1",
  title: "Natural Language Processing",
  professor: "Professor",
  term: "Summer 2026",
};

const session: LoginSession = {
  username: "student-a",
  term: "Summer 2026",
  roles: ["student"],
  courses: [],
  access_token: "test-token",
};

const source: PpiExamSource = {
  id: "ppi-42",
  ppi_lecture_id: 42,
  title: "Natural Language Processing",
  protocol_count: 5,
  imported_at: "2026-07-31T10:00:00Z",
  source_filename: "protocols.zip",
  archive_sha256: "b".repeat(64),
  files: [],
};

const catalog = {
  tokens: 1,
  cached_sources: [],
  lectures: [
    {
      id: 42,
      title: "Natural Language Processing",
      protocol_count: 5,
      borrowed: true,
      can_borrow: false,
      download_available: true,
    },
    {
      id: 43,
      title: "Probabilistic Machine Learning",
      protocol_count: 7,
      borrowed: true,
      can_borrow: false,
      download_available: true,
    },
  ],
};

function json(payload: unknown) {
  return Promise.resolve(jsonResponse(payload));
}

function jsonResponse(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
