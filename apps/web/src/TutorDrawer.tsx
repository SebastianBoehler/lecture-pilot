import { SendHorizontal } from "lucide-react";
import { FormEvent, KeyboardEvent, useState } from "react";

import type { ChatMessage } from "./types";

export function TutorDrawer({
  messages,
  model,
  onSendMessage,
}: {
  messages: ChatMessage[];
  model: string | null;
  onSendMessage: (message: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);

  async function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || isSending) {
      return;
    }

    setDraft("");
    setError(null);
    setIsSending(true);
    try {
      await onSendMessage(message);
    } catch (sendError) {
      setError(sendError instanceof Error ? sendError.message : "Tutor turn failed.");
    } finally {
      setIsSending(false);
    }
  }

  function handleDraftKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) {
      return;
    }
    event.preventDefault();
    event.currentTarget.form?.requestSubmit();
  }

  return (
    <aside className="drawer" aria-label="Tutor drawer">
      <div className="drawer-section">
        <div className="tutor-heading">
          <h2>Tutor</h2>
          <span className="tutor-status">{tutorStatus(model)}</span>
        </div>
        <div className="message-list" aria-live="polite">
          {messages.map((message) => (
            <div className={`chat-message ${message.role}`} key={message.id}>
              <p>{message.content}</p>
              {message.toolTags?.length ? (
                <div className="tool-tags" aria-label="Tool calls">
                  {message.toolTags.map((tag) => (
                    <span className="tool-tag" key={tag}>
                      {tag}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
        </div>
        <form className="chat-form" onSubmit={submitMessage}>
          <div className="chat-composer">
            <textarea
              aria-label="Tutor message"
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleDraftKeyDown}
              placeholder="Ask about this lecture..."
              rows={1}
              value={draft}
            />
            <button
              aria-label="Send message"
              className="chat-send-button"
              disabled={isSending || !draft.trim()}
              title="Send message"
              type="submit"
            >
              <SendHorizontal size={17} />
            </button>
          </div>
        </form>
        {error ? <p className="form-error">{error}</p> : null}
      </div>
    </aside>
  );
}

function tutorStatus(model: string | null) {
  if (model) {
    return model === "local-guided-preview" ? "Local guided preview" : `Model: ${model}`;
  }
  return "Model after first turn";
}
