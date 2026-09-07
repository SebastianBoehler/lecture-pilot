import { useContext, useState, type ReactNode } from "react";
import { useI18n } from "./i18n";
import { MathText } from "./MathText";
import { PredictionContext } from "./predictionContext";
import type { CanvasBlock } from "./types";

const copy = {
  en: {
    title: "Before you begin",
    intro: "What do you think? A guess is enough. This is private and ungraded.",
    label: "Your prediction",
    save: "Save prediction",
    skip: "Skip",
    saving: "Saving…",
    saved: "Your first prediction",
    revisit:
      "Continue with the explanation, then compare it with your first idea. You can also ask the tutor to revisit it.",
    skipped: "Skipped — continue when you're ready.",
    preview: "Students can save a short prediction or skip this question.",
    loading: "Loading your prediction…",
  },
  de: {
    title: "Bevor du beginnst",
    intro: "Was denkst du? Eine Vermutung genügt. Sie bleibt privat und wird nicht bewertet.",
    label: "Deine Vermutung",
    save: "Vermutung speichern",
    skip: "Überspringen",
    saving: "Wird gespeichert…",
    saved: "Deine erste Vermutung",
    revisit:
      "Lies die Erklärung und vergleiche sie danach mit deiner ersten Idee. Du kannst auch den Tutor darauf ansprechen.",
    skipped: "Übersprungen — mach weiter, wenn du bereit bist.",
    preview: "Studierende können eine kurze Vermutung speichern oder die Frage überspringen.",
    loading: "Deine Vermutung wird geladen…",
  },
};

export function PredictionBlock({
  block,
  className,
  sourceMarker,
}: {
  block: CanvasBlock;
  className: string;
  sourceMarker: ReactNode;
}) {
  const { locale } = useI18n();
  const text = copy[locale];
  const context = useContext(PredictionContext);
  const saved = context?.saved.find((item) => item.block_id === block.id);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function submit(value: string | null) {
    if (!context || busy) return;
    setBusy(true);
    setError(null);
    try {
      await context.save(block.id, value);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save prediction.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <aside className={`${className} canvas-checkpoint canvas-prediction`} id={block.id}>
      <strong>{block.caption || text.title}</strong>
      <p>{text.intro}</p>
      <MathText highlightedText={null} mode="block" text={block.text ?? ""} />
      {!context ? (
        <p>{text.preview}</p>
      ) : context.loading ? (
        <p role="status">{text.loading}</p>
      ) : saved ? (
        <div role="status">
          {saved.answer === null ? (
            <p>{text.skipped}</p>
          ) : (
            <>
              <strong>{text.saved}</strong>
              <p style={{ whiteSpace: "pre-wrap" }}>{saved.answer}</p>
              <p>{text.revisit}</p>
            </>
          )}
        </div>
      ) : (
        <form
          className="canvas-checkpoint-form"
          onSubmit={(event) => {
            event.preventDefault();
            void submit(answer.trim());
          }}
        >
          <label htmlFor={`${block.id}-prediction`}>{text.label}</label>
          <textarea
            id={`${block.id}-prediction`}
            rows={3}
            maxLength={2000}
            value={answer}
            disabled={busy || !!context.error}
            onChange={(event) => setAnswer(event.target.value)}
          />
          <div className="canvas-checkpoint-actions">
            <button
              className="primary-button"
              type="submit"
              disabled={busy || !answer.trim() || !!context.error}
            >
              {busy ? text.saving : text.save}
            </button>
            <button
              className="secondary-button"
              type="button"
              disabled={busy || !!context.error}
              onClick={() => void submit(null)}
            >
              {text.skip}
            </button>
          </div>
        </form>
      )}
      {context?.error || error ? (
        <p className="form-error" role="alert">
          {context?.error || error}
        </p>
      ) : null}
      {sourceMarker}
    </aside>
  );
}
