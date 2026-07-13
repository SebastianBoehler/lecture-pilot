import { useI18n } from "./i18n";

export function AppFooter({
  onOpenChangelog,
  onOpenHowItWorks,
  onOpenLearningScience,
  onOpenPrivacy,
}: {
  onOpenChangelog: () => void;
  onOpenHowItWorks: () => void;
  onOpenLearningScience: () => void;
  onOpenPrivacy: () => void;
}) {
  const { t } = useI18n();
  return (
    <footer className="app-footer">
      <nav aria-label={t("footer.info")}>
        <button type="button" onClick={onOpenChangelog}>
          {t("footer.changelog")}
        </button>
        <button type="button" onClick={onOpenHowItWorks}>
          {t("footer.howItWorks")}
        </button>
        <button type="button" onClick={onOpenLearningScience}>
          {t("footer.learningScience")}
        </button>
        <button type="button" onClick={onOpenPrivacy}>
          {t("footer.privacy")}
        </button>
      </nav>
      <p className="app-footer-signature">
        Built with{" "}
        <span role="img" aria-label="love">
          ♥
        </span>{" "}
        in Tübingen
      </p>
    </footer>
  );
}
