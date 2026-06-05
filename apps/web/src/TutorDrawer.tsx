import { SendHorizontal } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

import type { ChatMessage } from "./types";

export function TutorDrawer({
  messages,
  onSendMessage,
}: {
  messages: ChatMessage[];
  onSendMessage: (message: string) => Promise<void>;
}) {
  const tabs = useMemo(() => ["Summary", "Quiz", "Code", "Diagram"], []);
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
              {message.content}
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
      <div className="artifact-tabs" role="tablist" aria-label="Artifacts">
        {tabs.map((tab) => (
          <button role="tab" type="button" key={tab}>
            {tab}
          </button>
        ))}
      </div>
      <div className="artifact-card">
        <h3>Quiz: Feature Maps</h3>
        <p>Which part of the kernel trick avoids explicitly constructing feature vectors?</p>
      </div>
    </aside>
  );
}
