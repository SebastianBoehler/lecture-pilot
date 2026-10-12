import { HowItWorksArticle } from "./HowItWorksArticle";
import { LearningScienceArticle } from "./LearningScienceArticle";
import { InfoArticle } from "./InfoArticle";
import { privacyContent } from "./privacyContent";
import { useI18n } from "../i18n/i18n";
import type { InfoPageKind } from "../shared/types";

export function InfoPage({ kind }: { kind: InfoPageKind }) {
  const { locale, t } = useI18n();
  return (
    <main className="info-page is-how-it-works">
      {kind === "privacy" ? (
        <InfoArticle
          content={privacyContent[locale]}
          afterSection={{
            provider: (
              <p className="guide-links">
                <a
                  href="https://developers.openai.com/api/docs/guides/your-data"
                  target="_blank"
                  rel="noreferrer"
                >
                  {t("info.privacy.openAiLink")}
                </a>
              </p>
            ),
          }}
        />
      ) : kind === "learning-science" ? (
        <LearningScienceArticle />
      ) : (
        <HowItWorksArticle />
      )}
    </main>
  );
}
