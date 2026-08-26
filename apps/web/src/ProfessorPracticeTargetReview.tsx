import { useI18n } from "./i18n";
import { ProfessorPracticeTargetEditor } from "./ProfessorPracticeTargetEditor";
import type { PracticeTarget } from "./practiceDesignTypes";

export function ProfessorPracticeTargetReview({
  disabled,
  index,
  target,
  onChange,
}: {
  disabled: boolean;
  index: number;
  target: PracticeTarget;
  onChange: (target: PracticeTarget) => void;
}) {
  const { t } = useI18n();
  const stages = [
    {
      label: t("builder.design.baseline"),
      rationale: t("builder.design.baselineWhy"),
      task: target.baseline_task,
    },
    {
      label: t("builder.design.exit"),
      rationale: t("builder.design.exitWhy"),
      task: target.independent_exit_task,
    },
    {
      label: t("builder.design.transfer"),
      rationale: t("builder.design.transferWhy", { days: target.review_after_days }),
      task: target.delayed_transfer_task,
    },
  ];
  return (
    <section className="practice-target" role="listitem">
      <header>
        <strong>
          {t("builder.design.targetHeading", { number: index + 1, target: target.title })}
        </strong>
        <p>{target.outcome}</p>
      </header>
      <ol className="practice-sequence" aria-label={t("builder.design.sequenceLabel")}>
        {stages.map((stage, stageIndex) => (
          <li key={stage.label}>
            <span aria-hidden="true">{stageIndex + 1}</span>
            <div>
              <h4>{stage.label}</h4>
              <p className="practice-stage-rationale">{stage.rationale}</p>
              <p>{stage.task}</p>
            </div>
          </li>
        ))}
      </ol>
      <details className="practice-target-diagnostics">
        <summary>
          <span>{t("builder.design.inspectSupport")}</span>
          <span>
            {t("builder.design.supportCounts", {
              evidence: target.evidence_criteria.length,
              misconceptions: target.misconceptions.length,
              hints: target.hint_ladder.length,
            })}
          </span>
        </summary>
        <div className="practice-diagnostics-grid">
          <section>
            <h4>{t("builder.design.evidence")}</h4>
            <ul>
              {target.evidence_criteria.map((criterion) => (
                <li key={criterion.id}>{criterion.description}</li>
              ))}
            </ul>
          </section>
          <section>
            <h4>{t("builder.design.misconceptions")}</h4>
            <ul>
              {target.misconceptions.map((misconception) => (
                <li key={misconception.id}>{misconception.description}</li>
              ))}
            </ul>
          </section>
          <section>
            <h4>{t("builder.design.hints")}</h4>
            <ol>
              {target.hint_ladder.map((hint) => (
                <li key={hint.level}>
                  <strong>{t(`builder.design.hintLevels.${hint.level}`)}</strong>
                  <span>{hint.content}</span>
                </li>
              ))}
            </ol>
          </section>
        </div>
      </details>
      <p className="practice-source-note">
        {t("builder.design.sourceGrounding", { sources: target.source_refs.join(", ") })}
      </p>
      {!disabled ? (
        <ProfessorPracticeTargetEditor disabled={false} target={target} onChange={onChange} />
      ) : null}
    </section>
  );
}
