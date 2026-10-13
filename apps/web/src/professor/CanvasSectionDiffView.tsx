import { useState } from "react";

import { useI18n } from "../i18n/i18n";
import type { SectionDiff } from "./canvasSectionDiff";
import { SectionDiffItem } from "./diff/SectionDiffItem";
import "./diff/section-diff.css";

/** Per-lecture change summary, then each changed section; unchanged ones on request. */
export function CanvasSectionDiffView({ sections }: { sections: readonly SectionDiff[] }) {
  const { t } = useI18n();
  const [showUnchanged, setShowUnchanged] = useState(false);
  const count = (kind: SectionDiff["kind"]) =>
    sections.filter((section) => section.kind === kind).length;
  const unchanged = count("unchanged");
  if (unchanged === sections.length)
    return <p className="lecture-panel-help">{t("coursePage.draft.noChanges")}</p>;
  const changed = count("changed");
  const summary = [
    changed === 1
      ? t("courseDiff.summary.changedOne")
      : changed
        ? t("courseDiff.summary.changed", { count: changed })
        : null,
    count("added") ? t("courseDiff.summary.added", { count: count("added") }) : null,
    count("removed") ? t("courseDiff.summary.removed", { count: count("removed") }) : null,
    unchanged ? t("courseDiff.summary.unchanged", { count: unchanged }) : null,
  ].filter((item): item is string => Boolean(item));
  const shown = showUnchanged
    ? sections
    : sections.filter((section) => section.kind !== "unchanged");
  return (
    <div className="section-diff">
      <div className="section-diff-overview">
        <ul aria-label={t("courseDiff.summaryLabel")} className="section-diff-summary">
          {summary.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
        {unchanged ? (
          <label className="section-diff-unchanged-toggle">
            <input
              checked={showUnchanged}
              onChange={(event) => setShowUnchanged(event.target.checked)}
              type="checkbox"
            />
            {t("courseDiff.showUnchanged")}
          </label>
        ) : null}
      </div>
      {shown.map((section) => (
        <SectionDiffItem key={`${section.kind}-${section.id}`} section={section} />
      ))}
    </div>
  );
}
