import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "./i18n";
import { ProfessorLectureSchedule } from "./ProfessorLectureSchedule";
import type { LectureScheduleItem } from "./types";

const initialSchedule: LectureScheduleItem[] = [
  { number: "01", title: "Foundations", date: "2026-04-15", material_path: "Lecture01.tex" },
  { number: "02", title: "Regression", date: "2026-04-22", material_path: "Lecture02.tex" },
  { number: "03", title: "Clustering", date: "2026-04-29", material_path: "Lecture03.tex" },
];

describe("ProfessorLectureSchedule ordering", () => {
  it("uses shared column headings and omits raw material paths", () => {
    renderSchedule();

    const headings = document.querySelector(".lecture-schedule-column-headings");
    expect(headings).toHaveTextContent("Order");
    expect(headings).toHaveTextContent("Title");
    expect(headings).toHaveTextContent("Date");
    expect(document.querySelectorAll(".lecture-schedule-row-label")).toHaveLength(9);
    expect(screen.queryByText("Lecture01.tex")).not.toBeInTheDocument();
  });

  it("reorders rows by drag and drop and immediately renumbers them", () => {
    renderSchedule();

    const dataTransfer = {
      effectAllowed: "none",
      getData: vi.fn(() => "0"),
      setData: vi.fn(),
    };
    fireEvent.dragStart(screen.getByRole("spinbutton", { name: "Position of lecture 01" }), {
      dataTransfer,
    });
    fireEvent.dragOver(screen.getAllByRole("listitem")[2], { dataTransfer });
    fireEvent.drop(screen.getAllByRole("listitem")[2], { dataTransfer });

    expect(screen.getAllByLabelText("Title").map((input) => input.getAttribute("value"))).toEqual([
      "Regression",
      "Clustering",
      "Foundations",
    ]);
    expect(
      Array.from(document.querySelectorAll(".lecture-schedule-position-number")).map(
        (number) => number.textContent,
      ),
    ).toEqual(["01", "02", "03"]);
  });

  it("supports keyboard reordering from the grip", () => {
    renderSchedule();

    const grip = screen.getByRole("spinbutton", { name: "Position of lecture 03" });
    expect(grip).toHaveAttribute("aria-valuemin", "1");
    expect(grip).toHaveAttribute("aria-valuemax", "3");
    expect(grip).toHaveAttribute("aria-valuenow", "3");
    expect(grip).toHaveAttribute("aria-valuetext", "Clustering, position 3 of 3");
    expect(screen.queryAllByRole("button", { name: /^Move lecture/i })).toHaveLength(0);
    expect(screen.queryByLabelText("No.")).not.toBeInTheDocument();

    fireEvent.keyDown(grip, { key: "ArrowUp" });

    expect(screen.getAllByLabelText("Title").map((input) => input.getAttribute("value"))).toEqual([
      "Foundations",
      "Clustering",
      "Regression",
    ]);
    expect(
      screen.getByText("Drag a grip to reorder. Keyboard: focus a grip and use ↑ or ↓."),
    ).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Clustering moved to position 2.");
  });

  it("ignores drops that did not start from a schedule handle", () => {
    renderSchedule();

    fireEvent.drop(screen.getAllByRole("listitem")[2], {
      dataTransfer: { getData: vi.fn(() => "") },
    });

    expect(screen.getAllByLabelText("Title").map((input) => input.getAttribute("value"))).toEqual([
      "Foundations",
      "Regression",
      "Clustering",
    ]);
  });
});

function renderSchedule() {
  render(
    <I18nProvider locale="en" setLocale={vi.fn()}>
      <ScheduleHarness />
    </I18nProvider>,
  );
}

function ScheduleHarness() {
  const [schedule, setSchedule] = useState(initialSchedule);
  return (
    <ProfessorLectureSchedule
      disabled={false}
      isApplying={false}
      onApply={vi.fn()}
      onChange={setSchedule}
      schedule={schedule}
    />
  );
}
