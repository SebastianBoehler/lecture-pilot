import { useI18n } from "../i18n/i18n";
import { collapseUnchanged, type SectionDiff } from "./canvasSectionDiff";

/** Changed, added and removed sections; unchanged ones fold into one count. */
export function CanvasSectionDiffView({ sections }: { sections: readonly SectionDiff[] }) {
  const { t } = useI18n();
  const unchanged = sections.filter((section) => section.kind === "unchanged").length;
  const changes = sections.filter((section) => section.kind !== "unchanged");
  if (!changes.length)
    return <p className="lecture-panel-help">{t("coursePage.draft.noChanges")}</p>;
  return (
    <div className="section-diff">
      {changes.map((section) => (
        <article
          className="section-diff-item"
          data-kind={section.kind}
          key={`${section.kind}-${section.id}`}
        >
          <header>
            <span className="section-diff-kind">{t(`coursePage.draft.${section.kind}`)}</span>
            <h4>{section.title}</h4>
            {section.previousTitle ? (
              <span className="section-diff-renamed">
                {t("coursePage.draft.renamed", { title: section.previousTitle })}
              </span>
            ) : null}
          </header>
          <div className="section-diff-body">
            {(section.kind === "changed" ? collapseUnchanged(section.units) : section.units).map(
              (unit, index) =>
                unit.kind === "skipped" ? (
                  <p className="section-diff-skipped" key={index}>
                    {unit.count === 1
                      ? t("coursePage.draft.skippedOne")
                      : t("coursePage.draft.skipped", { count: unit.count })}
                  </p>
                ) : unit.kind === "same" ? (
                  <p className="section-diff-unit" key={index}>
                    {unit.text}
                  </p>
                ) : section.kind === "changed" ? (
                  <p className="section-diff-unit" data-change={unit.kind} key={index}>
                    <span className="visually-hidden">
                      {t(
                        unit.kind === "added"
                          ? "coursePage.draft.addedText"
                          : "coursePage.draft.removedText",
                      )}
                      :{" "}
                    </span>
                    {unit.kind === "added" ? <ins>{unit.text}</ins> : <del>{unit.text}</del>}
                  </p>
                ) : (
                  <p className="section-diff-unit" key={index}>
                    {unit.text}
                  </p>
                ),
            )}
          </div>
        </article>
      ))}
      {unchanged ? (
        <p className="section-diff-skipped">
          {unchanged === 1
            ? t("coursePage.draft.unchangedOne")
            : t("coursePage.draft.unchanged", { count: unchanged })}
        </p>
      ) : null}
    </div>
  );
}
