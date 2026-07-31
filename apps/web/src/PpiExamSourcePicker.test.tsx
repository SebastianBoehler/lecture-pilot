import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PpiExamSourcePicker } from "./PpiExamSourcePicker";
import type { PpiCatalogLecture } from "./practiceExamTypes";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LoginSession } from "./types";

describe("PpiExamSourcePicker", () => {
  it("filters the complete PPI catalog by course title", async () => {
    vi.stubGlobal("fetch", catalogFetch(catalogLectures));
    const user = userEvent.setup();
    renderPicker();

    await connect(user);
    expect(screen.getByRole("status")).toHaveTextContent("3 of 3 courses");

    await user.type(screen.getByLabelText("Search PPI courses"), "language");

    expect(screen.getByRole("status")).toHaveTextContent("1 of 3 courses");
    const results = screen.getByRole("list", { name: "PPI course results" });
    expect(within(results).getByText("Natural Language Processing")).toBeInTheDocument();
    expect(within(results).queryByText("Probabilistic Machine Learning")).not.toBeInTheDocument();
  });

  it("uses one explicit token-cost action instead of a per-row checkbox", async () => {
    const requests: RequestRecord[] = [];
    vi.stubGlobal("fetch", catalogFetch([catalogLectures[0]], requests));
    const user = userEvent.setup();
    renderPicker();

    await connect(user);
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    await user.click(
      screen.getByRole("button", {
        name: "Borrow for 1 token: Natural Language Processing",
      }),
    );

    await waitFor(() =>
      expect(requests.find((item) => item.url.endsWith("/imports"))?.body).toMatchObject({
        ppi_lecture_id: 42,
        confirm_token_spend: true,
      }),
    );
  });

  it("imports an already borrowed course without spending a token", async () => {
    const requests: RequestRecord[] = [];
    vi.stubGlobal(
      "fetch",
      catalogFetch(
        [{ ...catalogLectures[0], borrowed: true, can_borrow: false, download_available: true }],
        requests,
      ),
    );
    const user = userEvent.setup();
    renderPicker();

    await connect(user);
    await user.click(screen.getByRole("button", { name: "Import: Natural Language Processing" }));

    await waitFor(() =>
      expect(requests.find((item) => item.url.endsWith("/imports"))?.body).toMatchObject({
        confirm_token_spend: false,
      }),
    );
  });
});

function renderPicker() {
  return renderWithI18n(
    <PpiExamSourcePicker
      courseId="course-1"
      session={session}
      onImported={vi.fn()}
      onImportingChange={vi.fn()}
    />,
  );
}

async function connect(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "Import from PPI" }));
  await user.type(screen.getByLabelText("PPI username"), "zxabc12");
  await user.type(screen.getByLabelText("PPI password"), "ppi-secret");
  await user.click(screen.getByRole("button", { name: "Load PPI courses" }));
  await screen.findByLabelText("Search PPI courses");
}

type RequestRecord = { url: string; body?: Record<string, unknown> };

function catalogFetch(lectures: readonly PpiCatalogLecture[], requests: RequestRecord[] = []) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const body = init?.body
      ? (JSON.parse(String(init.body)) as Record<string, unknown>)
      : undefined;
    requests.push({ url, body });
    if (url.endsWith("/catalog")) {
      return json({ tokens: 1, cached_sources: [], lectures });
    }
    if (url.endsWith("/imports")) {
      return json({ source: ppiSource(), reused: false, token_spent: true });
    }
    return json([]);
  });
}

const catalogLectures = [
  {
    id: 42,
    title: "Natural Language Processing",
    protocol_count: 5,
    borrowed: false,
    can_borrow: true,
    download_available: false,
  },
  {
    id: 43,
    title: "Probabilistic Machine Learning",
    protocol_count: 7,
    borrowed: true,
    can_borrow: false,
    download_available: true,
  },
  {
    id: 44,
    title: "Software-Qualität in Theorie und Praxis",
    protocol_count: 10,
    borrowed: true,
    can_borrow: false,
    download_available: true,
  },
] as const;

const session: LoginSession = {
  username: "student-a",
  term: "Summer 2026",
  roles: ["student"],
  courses: [],
  access_token: "test-token",
};

function ppiSource() {
  return {
    id: "ppi-42",
    ppi_lecture_id: 42,
    title: "Natural Language Processing",
    protocol_count: 5,
    imported_at: "2026-07-31T10:00:00Z",
    source_filename: "protocols.zip",
    archive_sha256: "b".repeat(64),
    files: [],
  };
}

function json(payload: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}
