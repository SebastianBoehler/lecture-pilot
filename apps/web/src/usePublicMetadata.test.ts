import { renderHook } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { usePublicMetadata } from "./usePublicMetadata";
import { publicInformation } from "./publicInformation";
import type { View } from "./types";
import type { Locale } from "./i18n";

afterEach(() => {
  document.getElementById("public-information-jsonld")?.remove();
  document.querySelector('meta[name="description"]')?.remove();
});
it("keeps metadata in sync with public language changes and removes it on private views", () => {
  const hook = renderHook(
    ({ view, locale }: { view: View; locale: Locale }) => usePublicMetadata(view, locale),
    {
      initialProps: { view: "privacy" as View, locale: "en" as Locale },
    },
  );
  expect(document.title).toBe("Privacy and your data | LecturePilot");
  hook.rerender({ view: "privacy", locale: "de" });
  const metadata = JSON.parse(document.getElementById("public-information-jsonld")!.textContent!);
  expect(metadata.description).toBe(publicInformation.privacy.de.intro);
  hook.rerender({ view: "lesson", locale: "de" });
  expect(document.title).toBe("LecturePilot");
  expect(document.getElementById("public-information-jsonld")).toBeNull();
});
