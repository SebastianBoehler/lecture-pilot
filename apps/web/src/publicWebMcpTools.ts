import { pathForView } from "./appRoute";
import { publicInformation, type PublicInformationPage } from "./publicInformation";
import { validateWebMcpInput } from "./webMcpInput";
import type { WebMcpTool } from "./webMcpTypes";
import type { Locale } from "./i18n";

type PublicState = { locale: Locale; busy: boolean; navigate: (path: string) => void };
const pageSchema = { type: "string", enum: Object.keys(publicInformation) };

export function createPublicWebMcpTools(current: () => PublicState): WebMcpTool[] {
  return [
    {
      name: "lecturepilot_get_public_information",
      description:
        "Learn what LecturePilot is, its student and lecturer workflows, learning approach and privacy boundaries. Public information only; no account or course data. No login required.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        properties: { page: pageSchema, language: { type: "string", enum: ["en", "de"] } },
      },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      async execute(raw) {
        const input = validateWebMcpInput(
          raw,
          { page: pageSchema, language: { enum: ["en", "de"] } },
          [],
        );
        const language = (input.language ?? current().locale) as Locale;
        const page = (input.page ?? "how-it-works") as PublicInformationPage;
        return {
          name: "LecturePilot",
          language,
          page,
          path: pathForView(page),
          article: publicInformation[page][language],
          public_pages: Object.entries(publicInformation).map(([key, content]) => ({
            page: key,
            title: content[language].title,
            path: pathForView(key as PublicInformationPage),
          })),
          student_tools_require_authentication: true,
        };
      },
    },
    {
      name: "lecturepilot_open_public_page",
      description:
        "Open a public LecturePilot guide: how it works, learning science or privacy. No login required. Cannot open courses, assessments or account settings.",
      inputSchema: {
        type: "object",
        additionalProperties: false,
        properties: { page: pageSchema },
        required: ["page"],
      },
      annotations: { readOnlyHint: false, untrustedContentHint: false },
      async execute(raw) {
        const input = validateWebMcpInput(raw, { page: pageSchema }, ["page"]);
        const state = current();
        if (state.busy)
          throw new Error(
            "Let the student finish the current learning interaction before navigating.",
          );
        const path = pathForView(input.page as PublicInformationPage);
        state.navigate(path);
        return { path, navigation_requested: true };
      },
    },
  ];
}
