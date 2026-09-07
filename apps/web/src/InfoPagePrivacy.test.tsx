import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it } from "vitest";
import { I18nProvider } from "./i18n";
import { InfoPage } from "./InfoPage";
import type { InfoPageKind } from "./types";

beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});

function page(kind: InfoPageKind, locale: "en" | "de" = "en") {
  return (
    <I18nProvider locale={locale} setLocale={() => {}}>
      <InfoPage kind={kind} />
    </I18nProvider>
  );
}

it("explains disclosure, private analytics and incomplete retention details", () => {
  render(page("privacy"));
  expect(screen.getByText(/up to eight recent learner and tutor messages/)).toBeInTheDocument();
  expect(screen.getByText(/do not see ordinary private chat messages/)).toBeInTheDocument();
  expect(screen.getByText(/Professor preview activity is excluded/)).toBeInTheDocument();
  expect(screen.getByText(/does not promise zero provider retention/)).toBeInTheDocument();
  expect(
    screen.getByText(/designated data controller.*still require institutional confirmation/),
  ).toBeInTheDocument();
});

it.each(["privacy", "how-it-works", "learning-science"] as const)(
  "localizes %s and provides working chapter targets",
  (kind) => {
    const { container, rerender } = render(page(kind));
    const english = screen.getByRole("heading", { level: 1 }).textContent;
    rerender(page(kind, "de"));
    expect(screen.getByRole("heading", { level: 1 }).textContent).not.toBe(english);
    const nav = screen.getByRole("navigation", { name: "Auf dieser Seite" });
    for (const link of nav.querySelectorAll("a")) {
      expect(container.querySelector(link.getAttribute("href")!)).not.toBeNull();
    }
  },
);

it("opens the real chaptered onboarding from the lecturer guide", () => {
  render(page("how-it-works"));
  fireEvent.click(screen.getByRole("button", { name: "Watch introduction" }));
  expect(screen.getByRole("dialog")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Close/i })).toBeInTheDocument();
});
