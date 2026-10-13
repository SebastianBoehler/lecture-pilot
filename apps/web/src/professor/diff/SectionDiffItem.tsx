import { useId } from "react";

import { useI18n } from "../../i18n/i18n";
import type { SectionDiff } from "../canvasSectionDiff";
import { InlineSectionDiff } from "./InlineSectionDiff";
import { sectionShape } from "./sectionShape";
import { SideBySideDiff } from "./SideBySideDiff";
import { WholeSectionBody } from "./WholeSectionBody";

/** One section of the draft review with the layout that fits how much of it changed. */
export function SectionDiffItem({ section }: { section: SectionDiff }) {
  const { t } = useI18n();
  const headingId = useId();
  const shape = section.kind === "changed" ? sectionShape(section.units) : null;
  const count = section.units.length;
  return (
    <article
      aria-labelledby={headingId}
      className="section-diff-item"
      data-kind={section.kind}
      data-shape={shape ?? undefined}
    >
      <header>
        <span className="section-diff-kind">
          {section.kind === "unchanged"
            ? t("courseDiff.unchanged")
            : t(`coursePage.draft.${section.kind}`)}
        </span>
        <h4 id={headingId}>{section.title}</h4>
        {section.previousTitle ? (
          <span className="section-diff-meta">
            {t("coursePage.draft.renamed", { title: section.previousTitle })}
          </span>
        ) : null}
        {shape === "rewritten" ? (
          <span className="section-diff-meta">{t("courseDiff.rewritten")}</span>
        ) : null}
        {section.kind !== "changed" ? (
          <span className="section-diff-meta">
            {count === 1 ? t("courseDiff.paragraphsOne") : t("courseDiff.paragraphs", { count })}
          </span>
        ) : null}
      </header>
      {shape === "rewritten" ? (
        <SideBySideDiff units={section.units} />
      ) : shape === "edited" ? (
        <InlineSectionDiff units={section.units} />
      ) : (
        <WholeSectionBody folded={section.kind === "unchanged"} units={section.units} />
      )}
    </article>
  );
}
