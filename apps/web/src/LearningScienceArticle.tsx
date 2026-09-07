import { useI18n } from "./i18n";
import { InfoArticle } from "./InfoArticle";
import { learningGuideContent } from "./learningGuideContent";

const sources = [
  [
    "Biggs (1996). Enhancing teaching through constructive alignment.",
    "https://doi.org/10.1007/BF00138871",
  ],
  [
    "Roediger & Karpicke (2006). Test-enhanced learning: Taking memory tests improves long-term retention.",
    "https://doi.org/10.1111/j.1467-9280.2006.01693.x",
  ],
  [
    "Wagner et al. (2024). The more, the better? Learning with feedback and instruction.",
    "https://doi.org/10.1016/j.learninstruc.2023.101844",
  ],
  [
    "Cepeda et al. (2006). Distributed practice in verbal recall tasks: A review and quantitative synthesis.",
    "https://doi.org/10.1037/0033-2909.132.3.354",
  ],
  [
    "Pashler et al. (2008). Learning styles: Concepts and evidence.",
    "https://doi.org/10.1111/j.1539-6053.2009.01038.x",
  ],
];

export function LearningScienceArticle() {
  const { locale } = useI18n();
  return (
    <InfoArticle
      content={learningGuideContent[locale]}
      afterSection={{
        research: (
          <ol className="guide-links">
            {sources.map(([title, href]) => (
              <li key={href}>
                <a href={href} target="_blank" rel="noreferrer">
                  {title}
                </a>
              </li>
            ))}
          </ol>
        ),
      }}
    />
  );
}
