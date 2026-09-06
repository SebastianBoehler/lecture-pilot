import { MessageSquare, Trash2 } from "lucide-react";
import { useContext, useState, type ReactNode } from "react";

import { CanvasAnnotationContext } from "./canvasAnnotationContext";
import { MathText } from "./MathText";
import { useI18n } from "./i18n";
import "./canvas-annotations.css";

export function AnnotatedCanvasBlock({
  blockId,
  children,
}: {
  blockId: string;
  children: ReactNode;
}) {
  const context = useContext(CanvasAnnotationContext);
  const { locale } = useI18n();
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const notes = context?.annotations.filter((note) => note.block_id === blockId) ?? [];
  if (!notes.length) return children;
  const german = locale === "de";

  async function remove(id: string) {
    setDeleting(id);
    setError(null);
    try {
      await context?.remove(id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete comment.");
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="canvas-annotated-block">
      {children}
      <details className="canvas-annotation">
        <summary
          tabIndex={0}
          aria-label={`${german ? "Kommentare öffnen" : "Open comments"} (${notes.length})`}
          title={german ? "Private Kommentare" : "Private comments"}
        >
          <MessageSquare size={16} aria-hidden="true" />
          {notes.length > 1 ? <span>{notes.length}</span> : null}
        </summary>
        <div className="canvas-annotation-comments">
          {notes.map((note) => (
            <div key={note.id} className="canvas-annotation-comment">
              <div className="canvas-annotation-heading">
                <strong>{german ? "Private Kommentare" : "Private comments"}</strong>
                <button
                  type="button"
                  className="icon-button"
                  disabled={deleting !== null}
                  aria-label={german ? "Kommentar löschen" : "Delete comment"}
                  onClick={() => void remove(note.id)}
                >
                  <Trash2 size={14} aria-hidden="true" />
                </button>
              </div>
              {note.quote ? (
                <blockquote>
                  <MathText text={note.quote} highlightedText={null} />
                </blockquote>
              ) : null}
              <div className="canvas-annotation-body">
                <MathText text={note.comment} highlightedText={null} mode="block" />
              </div>
            </div>
          ))}
          {error ? (
            <p className="form-error" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      </details>
    </div>
  );
}
