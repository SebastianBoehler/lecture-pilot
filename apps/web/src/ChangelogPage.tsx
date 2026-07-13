import { useI18n } from "./i18n";
import { productChangelog, releaseUrl } from "./productChangelog";

export function ChangelogPage({ onBack }: { onBack: () => void }) {
  const { locale, t } = useI18n();
  const dateFormatter = new Intl.DateTimeFormat(locale === "de" ? "de-DE" : "en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });

  return (
    <main className="changelog-page">
      <button className="ghost-button info-back" type="button" onClick={onBack}>
        {t("info.back")}
      </button>
      <header className="changelog-header">
        <h1>{t("changelog.title")}</h1>
        <p>{t("changelog.intro")}</p>
      </header>
      <div className="changelog-releases" aria-label={t("changelog.history")}>
        {productChangelog.releases.map((release, index) => (
          <article className="changelog-release" key={release.version}>
            <div className="changelog-release-meta">
              <time dateTime={release.date}>
                {dateFormatter.format(new Date(`${release.date}T00:00:00Z`))}
              </time>
              <a
                aria-label={`v${release.version} ${t("changelog.onGitHub")}`}
                href={releaseUrl(release.version)}
                rel="noreferrer"
                target="_blank"
              >
                v{release.version}
              </a>
              {index === 0 ? <span>{t("changelog.latest")}</span> : null}
            </div>
            <h2>{release.title[locale]}</h2>
            <p className="changelog-summary">{release.summary[locale]}</p>
            <ul className="changelog-change-list">
              {release.changes.map((change) => (
                <li key={change.title.en}>
                  <div className="changelog-change-title">
                    <h3>{change.title[locale]}</h3>
                    {change.feedbackDriven ? (
                      <span className="changelog-feedback-label">
                        {t("changelog.feedbackDriven")}
                      </span>
                    ) : null}
                  </div>
                  <p>{change.description[locale]}</p>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </main>
  );
}
