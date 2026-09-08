import { expect, it } from "vitest";
import { renderPublicPage } from "../tooling/publicDiscovery";
import { publicInformation } from "./publicInformation";

it("renders every public guide as readable HTML with real links and matching metadata", () => {
  const shell =
    '<html><head><title>LecturePilot</title><meta name="description" content="old" /></head><body><div id="root"></div><script src="/assets/app.js"></script></body></html>';
  for (const page of Object.keys(publicInformation) as Array<keyof typeof publicInformation>) {
    const html = renderPublicPage(shell, page);
    const parsed = new DOMParser().parseFromString(html, "text/html");
    const article = publicInformation[page].en;
    expect(parsed.querySelector("h1")?.textContent).toBe(article.title);
    expect(parsed.querySelector('meta[name="description"]')?.getAttribute("content")).toBe(
      article.intro,
    );
    for (const section of article.sections) {
      expect(parsed.getElementById(section.id)?.textContent).toContain(section.paragraphs[0]);
    }
    expect(parsed.querySelector('a[href="/privacy"]')).not.toBeNull();
    expect(parsed.querySelector('script[src="/assets/app.js"]')).not.toBeNull();
    const metadata = JSON.parse(
      parsed.querySelector('script[type="application/ld+json"]')!.textContent!,
    );
    expect(metadata.description).toBe(article.intro);
    expect(html).not.toContain("/api/");
  }
});
