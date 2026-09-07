import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { I18nProvider } from "./i18n";
import { OnboardingVideo } from "./OnboardingVideo";

beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});

it("seeks to chapters, follows playback, and shows the matching instructions", () => {
  render(
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <OnboardingVideo />
    </I18nProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Watch introduction" }));
  const dialog = screen.getByRole("dialog");
  const nav = within(dialog).getByRole("navigation", { name: "Video chapters" });
  expect(within(nav).getAllByRole("button")).toHaveLength(10);
  fireEvent.click(within(nav).getByRole("button", { name: /Personalized explanations/ }));
  const video = within(dialog).getByLabelText("Introduction video") as HTMLVideoElement;
  expect(video.currentTime).toBe(417.167);
  expect(screen.getByText(/Request a new section to keep/)).toBeInTheDocument();
  video.currentTime = 490;
  fireEvent.timeUpdate(video);
  expect(within(nav).getByRole("button", { name: /Generate and download/ })).toHaveAttribute(
    "aria-current",
    "step",
  );
  expect(screen.getByText(/Take it in the browser or download/)).toBeInTheDocument();
  expect(video.autoplay).toBe(false);
  expect(video.querySelector('track[kind="captions"]')).toHaveAttribute("srclang", "en");
  fireEvent.error(video);
  expect(screen.getByRole("alert")).toHaveTextContent("could not be loaded");
  fireEvent(dialog, new Event("cancel", { bubbles: false }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("offers German chapter descriptions and closes using the visible action", () => {
  render(
    <I18nProvider locale="de" setLocale={vi.fn()}>
      <OnboardingVideo />
    </I18nProvider>,
  );
  fireEvent.click(screen.getByRole("button", { name: "Einführung ansehen" }));
  fireEvent.click(screen.getByRole("button", { name: /Lernziele prüfen/ }));
  expect(screen.getByText(/Geben Sie alle Lernziele frei/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Schließen" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
