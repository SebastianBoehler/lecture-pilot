import type { Plugin } from "vite";
import {
  publicInformation,
  publicPageMetadata,
  productDescription,
  type PublicInformationPage,
} from "../src/publicInformation";
import type { InfoArticleContent } from "../src/infoArticleTypes";

export function publicDiscovery(): Plugin {
  return {
    name: "lecturepilot-public-discovery",
    transformIndexHtml(html) {
      return html.replace(
        "</head>",
        `    <meta name="description" content="${escapeHtml(productDescription)}" />\n  </head>`,
      );
    },
    generateBundle: {
      order: "post",
      handler(_, bundle) {
        const index = bundle["index.html"];
        if (!index || index.type !== "asset" || typeof index.source !== "string") {
          throw new Error("Public discovery requires the built application index.html.");
        }
        for (const page of Object.keys(publicInformation) as PublicInformationPage[]) {
          this.emitFile({
            type: "asset",
            fileName: `${page}/index.html`,
            source: renderPublicPage(index.source, page),
          });
        }
        this.emitFile({ type: "asset", fileName: "llms.txt", source: publicAgentGuide() });
      },
    },
  };
}

export function renderPublicPage(shell: string, page: PublicInformationPage) {
  const content = publicInformation[page].en;
  const links = Object.entries(publicInformation)
    .map(([key, article]) => `<a href="/${key}">${escapeHtml(article.en.title)}</a>`)
    .join("\n");
  const article = `<main><article><h1>${escapeHtml(content.title)}</h1><p>${escapeHtml(content.intro)}</p>${renderSections(content)}</article><nav aria-label="Public guides">${links}</nav><a href="/">Sign in to LecturePilot</a></main>`;
  const structured = JSON.stringify(publicPageMetadata(page, "en")).replaceAll("<", "\\u003c");
  return shell
    .replace(/<title>.*?<\/title>/, `<title>${escapeHtml(content.title)} | LecturePilot</title>`)
    .replace(
      /<meta name="description" content="[^"]*"\s*\/>/,
      `<meta name="description" content="${escapeHtml(content.intro)}" />`,
    )
    .replace('<div id="root"></div>', `<div id="root">${article}</div>`)
    .replace(
      "</head>",
      `<script id="public-information-jsonld" type="application/ld+json">${structured}</script>\n</head>`,
    );
}

function renderSections(content: InfoArticleContent) {
  return content.sections
    .map(
      (section) =>
        `<section id="${escapeHtml(section.id)}"><h2>${escapeHtml(section.title)}</h2>${section.paragraphs.map((p) => `<p>${escapeHtml(p)}</p>`).join("")}${section.steps ? `<ol>${section.steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ol>` : ""}${section.example ? `<aside>${escapeHtml(section.example)}</aside>` : ""}${section.detail ? `<details><summary>More detail</summary><p>${escapeHtml(section.detail)}</p></details>` : ""}</section>`,
    )
    .join("");
}

function publicAgentGuide() {
  return `# LecturePilot\n\n> ${productDescription}\n\n## Public guides\n\n${Object.entries(
    publicInformation,
  )
    .map(([page, content]) => `- [${content.en.title}](/${page}): ${content.en.intro}`)
    .join(
      "\n",
    )}\n\n## Browser tools\n\nIn a supporting browser, public WebMCP tools can explain LecturePilot and open these guides without sign-in. Student tools require a backend-verified student session. They can navigate authorized courses, read bounded learning evidence, and change interface settings. They cannot submit answers, send tutor messages or change learning progress. The human student does the learning.\n\nPrivate course material, account data and learner work are not public discovery content.\n`;
}

function escapeHtml(value: string) {
  return value.replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]!,
  );
}
