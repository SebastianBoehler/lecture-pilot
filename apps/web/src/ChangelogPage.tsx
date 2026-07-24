import { useI18n } from "./i18n";
import { productChangelog, releaseUrl } from "./productChangelog";

export function ChangelogPage() {
  const { locale, t } = useI18n();
  const dateFormatter = new Intl.DateTimeFormat(locale === "de" ? "de-DE" : "en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });

  return (
    <main className="changelog-page">
      <header className="changelog-header">
        <h1>{t("changelog.title")}</h1>
      </header>
      <div className="changelog-releases" aria-label={t("changelog.history")}>
        {productChangelog.releases.map((release) => (
          <article className="changelog-release" key={release.version}>
            <h2>{release.title[locale]}</h2>
            <p className="changelog-release-meta">
              <time dateTime={release.date}>
                {dateFormatter.format(new Date(`${release.date}T00:00:00Z`))}
              </time>
              <span aria-hidden="true">·</span>
              <a
                aria-label={`v${release.version} ${t("changelog.onGitHub")}`}
                href={releaseUrl(release.version)}
                rel="noreferrer"
                target="_blank"
              >
                v{release.version}
              </a>
            </p>
            <p className="changelog-summary">{release.summary[locale]}</p>
            <ul className="changelog-change-list">
              {release.changes.map((change) => (
                <li key={change.title.en}>{change.title[locale]}</li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </main>
  );
}
