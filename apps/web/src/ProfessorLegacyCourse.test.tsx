import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { localProfessorSession } from "./appDefaults";
import { ProfessorCourseManagement } from "./ProfessorCourseManagement";
import { renderWithI18n } from "./test/renderWithI18n";

it.each(["en", "de"] as const)(
  "shows a private legacy course with an owner delete action in %s",
  async (locale) => {
    const user = userEvent.setup();
    let deleted = false;
    const confirm = vi.fn(() => true);
    vi.stubGlobal("confirm", confirm);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const path = new URL(String(input), "http://localhost").pathname;
        if (path === "/admin/courses" && !init?.method) return json(deleted ? [] : [workspace]);
        if (path === "/admin/courses/legacy-gdml" && init?.method === "DELETE") {
          deleted = true;
          return json({ course_id: "legacy-gdml", deleted: true });
        }
        throw new Error(`Unexpected request ${path}`);
      }),
    );
    renderWithI18n(
      <ProfessorCourseManagement
        onCreateCourse={() => undefined}
        onWorkspaceDeleted={() => undefined}
        session={localProfessorSession}
      />,
      { locale },
    );
    const title = await screen.findByText("GDML preserved course");
    const row = title.closest("article")!;
    expect(
      within(row.querySelector(".created-course-status")!).getByText("Legacy"),
    ).toBeInTheDocument();
    expect(within(row).queryByText(locale === "en" ? "Draft" : "Entwurf")).not.toBeInTheDocument();
    expect(
      within(row).getByText(locale === "en" ? "Private" : "Privat", { selector: "strong" }),
    ).toBeInTheDocument();
    expect(
      within(row).getByText(
        locale === "en"
          ? /Older publications cannot be opened/
          : /Ältere Veröffentlichungen können/,
      ),
    ).toBeInTheDocument();
    expect(
      within(row).queryByRole("button", {
        name: locale === "en" ? "Open lecture" : "Vorlesung öffnen",
      }),
    ).not.toBeInTheDocument();
    await user.click(
      within(row).getByRole("button", {
        name: locale === "en" ? "Delete GDML preserved course" : "GDML preserved course löschen",
      }),
    );
    expect(confirm).toHaveBeenCalledOnce();
    expect(
      await screen.findByText(
        locale === "en"
          ? /Course workspace legacy-gdml deleted/
          : /Kursarbeitsbereich legacy-gdml gelöscht/,
      ),
    ).toBeInTheDocument();
  },
);

const workspace = {
  course: {
    id: "legacy-gdml",
    title: "GDML preserved course",
    professor: "Professor",
    term: "Sommer 2026",
    access_policy: "instructors_only",
  },
  lectures: [
    { id: "lecture-01", course_id: "legacy-gdml", title: "Introduction", date: "2026-07-01" },
  ],
  active_lecture_id: "lecture-01",
  published_lecture_ids: [],
  legacy_lecture_ids: ["lecture-01"],
  access_summary: {
    course_id: "legacy-gdml",
    default_rule: {
      audience: "instructors_only",
      publication_mode: "hidden",
      publication_at: null,
    },
    lectures: [
      {
        lecture_id: "lecture-01",
        rule_source: "course_default",
        rule: { audience: "instructors_only", publication_mode: "hidden", publication_at: null },
        effective_publication_at: null,
        release_status: "hidden",
        content_ready: false,
      },
    ],
  },
};

function json(value: unknown) {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
