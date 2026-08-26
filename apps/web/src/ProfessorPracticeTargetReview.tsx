import { useI18n } from "./i18n";
import { ProfessorPracticeEvidence } from "./ProfessorPracticeEvidence";
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
      anchor: target.baseline_task_anchor,
      surfaceChange: null,
    },
    {
      label: t("builder.design.exit"),
      rationale: t("builder.design.exitWhy"),
      task: target.independent_exit_task,
      anchor: target.independent_exit_task_anchor,
      surfaceChange: target.independent_exit_surface_change,
    },
    {
      label: t("builder.design.transfer"),
      rationale: t("builder.design.transferWhy", { days: target.review_after_days }),
      task: target.delayed_transfer_task,
      anchor: target.delayed_transfer_task_anchor,
      surfaceChange: target.delayed_transfer_surface_change,
    },
  ];
  return (
    <section className="practice-target" role="listitem">
      <header>
        <strong>
          {t("builder.design.targetHeading", { number: index + 1, target: target.title })}
        </strong>
        <p>{target.outcome}</p>
        <ProfessorPracticeEvidence anchor={target.outcome_anchor} />
      </header>
      <div className="practice-target-invariant">
        <h4>{t("builder.design.invariant")}</h4>
        <p>{target.target_invariant}</p>
        <ProfessorPracticeEvidence anchor={target.target_invariant_anchor} />
      </div>
      <ol className="practice-sequence" aria-label={t("builder.design.sequenceLabel")}>
        {stages.map((stage, stageIndex) => (
          <li key={stage.label}>
            <span aria-hidden="true">{stageIndex + 1}</span>
            <div>
              <h4>{stage.label}</h4>
              <p className="practice-stage-rationale">{stage.rationale}</p>
              <p>{stage.task}</p>
              {stage.surfaceChange ? (
                <p className="practice-surface-change">
                  <strong>{t("builder.design.controlledChange")}</strong> {stage.surfaceChange}
                </p>
              ) : null}
              <ProfessorPracticeEvidence anchor={stage.anchor} />
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
                <li key={criterion.id}>
                  <span>{criterion.description}</span>
                  <ProfessorPracticeEvidence anchor={criterion.source_anchor} />
                </li>
              ))}
            </ul>
          </section>
          <section>
            <h4>{t("builder.design.misconceptions")}</h4>
            <ul>
              {target.misconceptions.map((misconception) => (
                <li key={misconception.id}>
                  <span>{misconception.description}</span>
                  <ProfessorPracticeEvidence anchor={misconception.source_anchor} />
                </li>
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
                  <ProfessorPracticeEvidence anchor={hint.source_anchor} />
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
