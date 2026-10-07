import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";

import type { PublishedLanguages } from "./canvasLanguageApi";
import { renderWithI18n } from "./test/renderWithI18n";
import type { LoginSession } from "./types";
import { useTeachingLanguage } from "./useTeachingLanguage";

const session = { tenant_id: "t", username: "student" } as LoginSession;

function Harness({ enabled = true }: { enabled?: boolean }) {
  return useTeachingLanguage("course", "lecture-01", session, null, 3, enabled).control;
}

function respond(payload: PublishedLanguages) {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => payload });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

const variant = {
  language: "de" as const,
  digest: "d",
  publication_version: 3,
  texts: [],
  published_at: null,
};

it("stays hidden when no reviewed translation exists for the current publication", async () => {
  const fetchMock = respond({
    canonical_language: "en",
    variants: [{ ...variant, publication_version: 2 }],
    unavailable_languages: [],
    originals: [],
  });
  const { container } = renderWithI18n(<Harness />);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  expect(container).toBeEmptyDOMElement();
  expect(screen.queryByRole("button", { name: /teaching language/i })).not.toBeInTheDocument();
});

it("offers a localized explanation language picker without a load step", async () => {
  respond({
    canonical_language: "en",
    variants: [variant],
    unavailable_languages: [],
    originals: [],
  });
  renderWithI18n(<Harness />, { locale: "de" });
  const picker = await screen.findByRole("combobox", { name: "Erklärungen" });
  expect(screen.getByRole("option", { name: "Originalfassung" })).toBeInTheDocument();
  await userEvent.selectOptions(picker, "de");
  expect(screen.getByText("Lernchecks bleiben auf Englisch.")).toBeInTheDocument();
});

it("does not request languages while disabled", () => {
  const fetchMock = respond({
    canonical_language: null,
    variants: [],
    unavailable_languages: [],
    originals: [],
  });
  renderWithI18n(<Harness enabled={false} />);
  expect(fetchMock).not.toHaveBeenCalled();
});

it("ignores a malformed language payload instead of breaking the lecture", async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ items: [] }) });
  vi.stubGlobal("fetch", fetchMock);
  const { container } = renderWithI18n(<Harness />);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
  expect(container).toBeEmptyDOMElement();
});
