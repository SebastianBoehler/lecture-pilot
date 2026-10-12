import { useI18n } from "../i18n/i18n";
import { InfoArticle } from "./InfoArticle";
import { howItWorksContent } from "./howItWorksContent";
import { OnboardingVideo } from "./OnboardingVideo";

export function HowItWorksArticle() {
  const { locale, t } = useI18n();
  return (
    <InfoArticle
      content={howItWorksContent[locale]}
      afterSection={{
        lecturers: (
          <div className="guide-video">
            <OnboardingVideo />
            <span>{t("howItWorks.video")}</span>
          </div>
        ),
        behind: (
          <figure className="guide-workspace">
            <div>
              <strong>{t("howItWorks.workspace.course")}</strong>
              <p>{t("howItWorks.workspace.courseDetail")}</p>
            </div>
            <div>
              <strong>{t("howItWorks.workspace.learner")}</strong>
              <p>{t("howItWorks.workspace.learnerDetail")}</p>
            </div>
            <div>
              <strong>{t("howItWorks.workspace.preferences")}</strong>
              <p>{t("howItWorks.workspace.preferencesDetail")}</p>
            </div>
            <figcaption>{t("howItWorks.workspace.caption")}</figcaption>
          </figure>
        ),
      }}
    />
  );
}
