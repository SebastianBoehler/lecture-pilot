import { useEffect, useState } from "react";

import { useI18n } from "./i18n";
import type { LearningDesignReview, LearningDesignUpdate } from "./learningDesignTypes";

export function ProfessorLearningDesignReview({
  lectureId,
  previewHref,
  review,
  saving,
  onApprove,
  onSave,
}: {
  lectureId: string;
  previewHref: string;
  review: LearningDesignReview;
  saving: boolean;
  onApprove: (lectureId: string) => void;
  onSave: (lectureId: string, update: LearningDesignUpdate) => void;
}) {
  const { t } = useI18n();
  const [update, setUpdate] = useState(() => editableReview(review));
  useEffect(() => setUpdate(editableReview(review)), [review]);
  const dirty = JSON.stringify(update) !== JSON.stringify(editableReview(review));
  return (
    <section className="learning-design-review">
      <h3>{t("builder.learningDesign.title")}</h3>
      <p>{t("builder.learningDesign.factualSeparate")}</p>
      <div className="learning-design-grid">
        <iframe src={previewHref} title={t("builder.learningDesign.preview")} />
        <div className="learning-design-fields">
          <label>
            {t("builder.learningDesign.objective")}
            <textarea
              value={update.objective}
              onChange={(event) => setUpdate({ ...update, objective: event.target.value })}
            />
          </label>
          {update.gates.map((gate, gateIndex) => {
            const source = review.learning_map.gates[gateIndex]?.source_ref;
            return (
              <fieldset key={gate.id}>
                <legend>{review.learning_map.gates[gateIndex]?.title ?? gate.id}</legend>
                {source ? <small>{source}</small> : null}
                <label>
                  {t("builder.learningDesign.prompt")}
                  <textarea
                    value={gate.prompt}
                    onChange={(event) =>
                      setUpdate({
                        ...update,
                        gates: replaceAt(update.gates, gateIndex, {
                          ...gate,
                          prompt: event.target.value,
                        }),
                      })
                    }
                  />
                </label>
                {gate.evidence_criteria.map((criterion, criterionIndex) => (
                  <label key={criterion.id}>
                    {t("builder.learningDesign.evidence")}
                    <textarea
                      value={criterion.description}
                      onChange={(event) =>
                        setUpdate({
                          ...update,
                          gates: replaceAt(update.gates, gateIndex, {
                            ...gate,
                            evidence_criteria: replaceAt(gate.evidence_criteria, criterionIndex, {
                              ...criterion,
                              description: event.target.value,
                            }),
                          }),
                        })
                      }
                    />
                  </label>
                ))}
                <label>
                  {t("builder.learningDesign.transfer")}
                  <textarea
                    value={gate.transfer_prompt ?? ""}
                    onChange={(event) =>
                      setUpdate({
                        ...update,
                        gates: replaceAt(update.gates, gateIndex, {
                          ...gate,
                          transfer_prompt: event.target.value || null,
                        }),
                      })
                    }
                  />
                </label>
                <label>
                  {t("builder.learningDesign.interval")}
                  <input
                    min="1"
                    max="365"
                    type="number"
                    value={gate.review_after_days}
                    onChange={(event) =>
                      setUpdate({
                        ...update,
                        gates: replaceAt(update.gates, gateIndex, {
                          ...gate,
                          review_after_days: Number(event.target.value),
                        }),
                      })
                    }
                  />
                </label>
              </fieldset>
            );
          })}
          <Prerequisites review={review} update={update} onChange={setUpdate} />
          {review.warnings.length ? (
            <div role="status">
              <strong>{t("builder.learningDesign.warnings")}</strong>
              <ul>
                {review.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <div className="learning-design-actions">
            <button disabled={saving} type="button" onClick={() => onSave(lectureId, update)}>
              {t("builder.learningDesign.save")}
            </button>
            <button
              disabled={saving || dirty || Boolean(review.approval)}
              type="button"
              onClick={() => onApprove(lectureId)}
            >
              {review.approval
                ? t("builder.learningDesign.approved")
                : t("builder.learningDesign.approve")}
            </button>
          </div>
          {dirty ? <p role="status">{t("builder.learningDesign.saveBeforeApprove")}</p> : null}
        </div>
      </div>
    </section>
  );
}

function Prerequisites({
  review,
  update,
  onChange,
}: {
  review: LearningDesignReview;
  update: LearningDesignUpdate;
  onChange: (update: LearningDesignUpdate) => void;
}) {
  const { t } = useI18n();
  return (
    <fieldset>
      <legend>{t("builder.learningDesign.prerequisites")}</legend>
      {update.prerequisites.map((item, index) => (
        <label key={item.section_id}>
          {review.learning_map.nodes[index]?.title ?? item.section_id}
          <select
            multiple
            value={item.prerequisite_ids}
            onChange={(event) =>
              onChange({
                ...update,
                prerequisites: replaceAt(update.prerequisites, index, {
                  ...item,
                  prerequisite_ids: Array.from(
                    event.target.selectedOptions,
                    (option) => option.value,
                  ),
                }),
              })
            }
          >
            {review.learning_map.nodes
              .filter((node) => node.section_id !== item.section_id)
              .map((node) => (
                <option key={node.section_id} value={node.section_id}>
                  {node.title}
                </option>
              ))}
          </select>
        </label>
      ))}
    </fieldset>
  );
}

function editableReview(review: LearningDesignReview): LearningDesignUpdate {
  return {
    draft_digest: review.draft_digest,
    source_revision: review.source_revision,
    learning_map_revision: review.learning_map.revision,
    objective: review.learning_map.objective,
    gates: review.learning_map.gates.map((gate) => ({
      id: gate.id,
      prompt: gate.prompt,
      evidence_criteria: gate.evidence_criteria,
      transfer_prompt: gate.transfer_prompt,
      review_after_days: gate.review_after_days,
    })),
    prerequisites: review.learning_map.nodes.map((node) => ({
      section_id: node.section_id,
      prerequisite_ids: node.prerequisites,
    })),
  };
}

function replaceAt<T>(items: T[], index: number, value: T): T[] {
  return items.map((item, itemIndex) => (itemIndex === index ? value : item));
}
