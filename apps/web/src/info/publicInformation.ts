import { howItWorksContent } from "./howItWorksContent";
import { learningGuideContent } from "./learningGuideContent";
import { privacyContent } from "./privacyContent";

export const publicInformation = {
  "how-it-works": howItWorksContent,
  "learning-science": learningGuideContent,
  privacy: privacyContent,
};
export type PublicInformationPage = keyof typeof publicInformation;
export const productDescription =
  "LecturePilot is a university course tutor for working through published lecture material, practising independently, and reviewing learning progress. Students do the learning; lecturers review and publish course content.";

export function publicPageMetadata(page: PublicInformationPage, language: "en" | "de") {
  const article = publicInformation[page][language];
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: article.title,
    description: article.intro,
    inLanguage: language,
    about: {
      "@type": "SoftwareApplication",
      name: "LecturePilot",
      applicationCategory: "EducationalApplication",
    },
  };
}
