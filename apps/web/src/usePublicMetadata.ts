import { useEffect } from "react";
import {
  productDescription,
  publicInformation,
  publicPageMetadata,
  type PublicInformationPage,
} from "./publicInformation";
import type { Locale } from "./i18n";
import type { View } from "./types";

export function usePublicMetadata(view: View, locale: Locale) {
  useEffect(() => {
    const metadata = Object.hasOwn(publicInformation, view)
      ? publicPageMetadata(view as PublicInformationPage, locale)
      : null;
    document.title = metadata ? `${metadata.name} | LecturePilot` : "LecturePilot";
    let description = document.querySelector<HTMLMetaElement>('meta[name="description"]');
    if (!description) {
      description = document.createElement("meta");
      description.name = "description";
      document.head.append(description);
    }
    description.content = metadata?.description ?? productDescription;
    document.getElementById("public-information-jsonld")?.remove();
    if (metadata) {
      const script = document.createElement("script");
      script.id = "public-information-jsonld";
      script.type = "application/ld+json";
      script.textContent = JSON.stringify(metadata).replaceAll("<", "\\u003c");
      document.head.append(script);
    }
  }, [view, locale]);
}
