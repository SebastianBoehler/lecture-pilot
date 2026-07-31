import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PracticeExamPanel } from "./PracticeExamPanel";
import { readPracticeExamDraft } from "./practiceExamDraft";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LoginSession, UniversityCourse } from "./types";

describe("PracticeExamPanel", () => {
  it("opens the setup in the browser modal layer", async () => {
    const originalShowModal = HTMLDialogElement.prototype.showModal;
    const showModal = vi.fn(function (this: HTMLDialogElement) {
      this.setAttribute("open", "");
    });
    Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
      configurable: true,
      value: showModal,
    });

    try {
      vi.stubGlobal("fetch", listFetch([], []));
      const user = userEvent.setup();
      renderPanel();
      await screen.findByRole("heading", { name: "Practice exams" });
      await user.click(screen.getByRole("button", { name: "Generate exam" }));

      expect(showModal).toHaveBeenCalledOnce();
      expect(screen.getByRole("dialog", { name: "Generate practice exam" })).toHaveAttribute(
        "open",
      );
    } finally {
      if (originalShowModal) {
        Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
          configurable: true,
          value: originalShowModal,
        });
      } else {
        Reflect.deleteProperty(HTMLDialogElement.prototype, "showModal");
      }
    }
  });

  it("shows the empty state and 25 question / 90 minute defaults", async () => {
    vi.stubGlobal("fetch", listFetch([], []));
    const user = userEvent.setup();
    renderPanel();

    expect(await screen.findByRole("heading", { name: "Practice exams" })).toBeInTheDocument();
    expect(
      screen.getByText(/full-length exams from unlocked course material/i),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Generate exam" }));

    const dialog = screen.getByRole("dialog", { name: "Generate practice exam" });
    const questionInput = within(dialog).getByLabelText("Questions");
    expect(questionInput).toHaveValue(25);
    expect(questionInput).toHaveAttribute("max", "50");
    expect(within(dialog).getByLabelText("Duration in minutes")).toHaveValue(90);
    await user.clear(questionInput);
    await user.type(questionInput, "50");
    expect(within(dialog).getByRole("button", { name: "Generate 50-question exam" })).toBeEnabled();
  });

  it("reuses cached PPI material without asking for credentials", async () => {
    vi.stubGlobal("fetch", listFetch([], [ppiSource()]));
    const user = userEvent.setup();
    renderPanel();
    await screen.findByRole("heading", { name: "Practice exams" });
    await user.click(screen.getByRole("button", { name: "Generate exam" }));

    const dialog = screen.getByRole("dialog", { name: "Generate practice exam" });
    expect(
      within(dialog).getByRole("checkbox", { name: /Machine Learning.*7 protocols/i }),
    ).toBeInTheDocument();
    expect(within(dialog).queryByLabelText("PPI password")).not.toBeInTheDocument();
  });

  it("imports an already-borrowed PPI lecture without token confirmation", async () => {
    const requests: Array<{ url: string; body?: Record<string, unknown> }> = [];
    vi.stubGlobal("fetch", ppiFetch(requests, true));
    const user = userEvent.setup();
    renderPanel();
    await screen.findByRole("heading", { name: "Practice exams" });
    await user.click(screen.getByRole("button", { name: "Generate exam" }));
    await user.click(screen.getByRole("button", { name: "Import from PPI" }));

    expect(screen.getByText(/PPI uses a separate account password/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText("PPI username"), "zxabc12");
    await user.type(screen.getByLabelText("PPI password"), "ppi-secret");
    await user.click(screen.getByRole("button", { name: "Load PPI courses" }));
    await user.click(await screen.findByRole("button", { name: "Import without token" }));

    await waitFor(() =>
      expect(requests.find((item) => item.url.endsWith("/imports"))?.body).toMatchObject({
        ppi_lecture_id: 42,
        confirm_token_spend: false,
      }),
    );
  });

  it("requires an exact one-token confirmation before borrowing", async () => {
    const requests: Array<{ url: string; body?: Record<string, unknown> }> = [];
    vi.stubGlobal("fetch", ppiFetch(requests, false));
    const user = userEvent.setup();
    renderPanel();
    await screen.findByRole("heading", { name: "Practice exams" });
    await user.click(screen.getByRole("button", { name: "Generate exam" }));
    await user.click(screen.getByRole("button", { name: "Import from PPI" }));
    await user.type(screen.getByLabelText("PPI username"), "zxabc12");
    await user.type(screen.getByLabelText("PPI password"), "ppi-secret");
    await user.click(screen.getByRole("button", { name: "Load PPI courses" }));

    const borrow = await screen.findByRole("button", { name: "Borrow and import" });
    expect(borrow).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: /spend one PPI token/i }));
    await user.click(borrow);

    await waitFor(() =>
      expect(requests.find((item) => item.url.endsWith("/imports"))?.body).toMatchObject({
        confirm_token_spend: true,
      }),
    );
  });

  it("generates one online exam and keeps answers only in the tab draft", async () => {
    vi.stubGlobal("fetch", generationFetch());
    const user = userEvent.setup();
    renderPanel();
    await screen.findByRole("heading", { name: "Practice exams" });
    await user.click(screen.getByRole("button", { name: "Generate exam" }));
    await user.click(screen.getByRole("button", { name: "Generate 25-question exam" }));

    const exam = await screen.findByRole("dialog", { name: "Practice exam" });
    await user.type(within(exam).getByLabelText("Your answer for question 2"), "My answer");

    expect(readPracticeExamDraft("student-a", "course-1", "a".repeat(32))).toEqual({
      "q-02": { text: "My answer" },
    });
  });

  it("offers direct open, PDF, and delete actions while clearing a deleted draft", async () => {
    vi.stubGlobal("fetch", existingExamFetch());
    vi.stubGlobal(
      "confirm",
      vi.fn(() => true),
    );
    const user = userEvent.setup();
    renderPanel();

    const examRow = await screen.findByRole("listitem");
    const openButton = within(examRow).getByRole("button", { name: "Open" });
    const pdfButton = within(examRow).getByRole("button", { name: "Download PDF" });
    const deleteButton = within(examRow).getByRole("button", { name: "Delete exam" });
    expect(openButton).toHaveTextContent("Open");
    expect(pdfButton).toHaveAttribute("title", "Download PDF");
    expect(deleteButton).toHaveAttribute("title", "Delete exam");

    await user.click(openButton);
    await user.type(screen.getByLabelText("Your answer for question 2"), "Temporary");
    await user.click(screen.getByRole("button", { name: "Close exam" }));
    await user.click(pdfButton);
    expect(await screen.findByRole("alert")).toHaveTextContent("Compiler unavailable");
    await user.click(deleteButton);
    await waitFor(() =>
      expect(readPracticeExamDraft("student-a", "course-1", "a".repeat(32))).toEqual({}),
    );
  });

  it("ships the practice exam flow in German", async () => {
    vi.stubGlobal("fetch", listFetch([], []));
    renderPanel("de");
    expect(await screen.findByRole("heading", { name: "Übungsprüfungen" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Prüfung erstellen" })).toBeInTheDocument();
  });
});

function renderPanel(locale: "en" | "de" = "en") {
  return renderWithI18n(<PracticeExamPanel course={course} session={session} />, { locale });
}

const session: LoginSession = {
  username: "student-a",
  term: "Summer 2026",
  roles: ["student"],
  courses: [],
  access_token: "test-token",
};
const course: UniversityCourse = {
  id: "course-1",
  title: "Machine Learning",
  professor: "Professor Example",
  term: "Summer 2026",
};

function listFetch(exams: unknown[], sources: unknown[]) {
  return vi.fn(async (input: RequestInfo | URL) =>
    json(String(input).endsWith("/ppi-exam-sources") ? sources : exams),
  );
}

function ppiFetch(
  requests: Array<{ url: string; body?: Record<string, unknown> }>,
  borrowed: boolean,
) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const body = init?.body
      ? (JSON.parse(String(init.body)) as Record<string, unknown>)
      : undefined;
    requests.push({ url, body });
    if (url.endsWith("/catalog"))
      return json({
        tokens: 2,
        cached_sources: [],
        lectures: [
          {
            id: 42,
            title: "Machine Learning",
            protocol_count: 7,
            borrowed,
            can_borrow: !borrowed,
            download_available: borrowed,
          },
        ],
      });
    if (url.endsWith("/imports"))
      return json({ source: ppiSource(), reused: false, token_spent: !borrowed });
    return json([]);
  });
}

function generationFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/practice-exam-generations")) return json(exam());
    return json([]);
  });
}

function existingExamFetch() {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/pdf")) return json({ detail: "Compiler unavailable" }, 503);
    if (init?.method === "DELETE") return json({ deleted: true });
    if (url.endsWith("/practice-exams")) return json([exam()]);
    return json([]);
  });
}

function exam() {
  return {
    id: "a".repeat(32),
    course_id: "course-1",
    title: "Practice exam",
    language: "en",
    instructions: ["Answer all questions."],
    duration_minutes: 90,
    created_at: "2026-07-31T10:00:00Z",
    total_points: 4,
    questions: [
      {
        id: "q-01",
        kind: "multiple_choice",
        prompt: "Choose one.",
        points: 2,
        options: ["A", "B"],
      },
      { id: "q-02", kind: "open_ended", prompt: "Explain risk.", points: 2, options: [] },
    ],
  };
}

function ppiSource() {
  return {
    id: "ppi-42",
    ppi_lecture_id: 42,
    title: "Machine Learning",
    protocol_count: 7,
    imported_at: "2026-07-31T10:00:00Z",
    source_filename: "protocols.zip",
    archive_sha256: "b".repeat(64),
    files: [],
  };
}

function json(payload: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
}
