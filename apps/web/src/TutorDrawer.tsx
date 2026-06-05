import { SendHorizontal } from "lucide-react";
import { FormEvent, useState } from "react";

import type { ChatMessage } from "./types";

export function TutorDrawer({
  messages,
  onSendMessage,
}: {
  messages: ChatMessage[];
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

  return (
    <aside className="drawer" aria-label="Tutor drawer">
      <div className="drawer-section">
        <h2>Tutor</h2>
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
          <textarea
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Ask about this lecture..."
            rows={4}
            value={draft}
          />
          <button aria-label="Send message" disabled={isSending || !draft.trim()} type="submit">
            <SendHorizontal size={16} />
            <span>{isSending ? "Sending" : "Send"}</span>
          </button>
        </form>
        {error ? <p className="form-error">{error}</p> : null}
      </div>
    </aside>
  );
}
