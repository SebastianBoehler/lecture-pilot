import { SendHorizontal } from "lucide-react";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

import { MathText } from "./MathText";
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
  const messageListRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const list = messageListRef.current;
    if (list) {
      list.scrollTop = list.scrollHeight;
    }
  }, [messages.length]);

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
    <aside className="drawer tutor-drawer" aria-label="Tutor drawer">
      <div className="drawer-section tutor-drawer-section">
        <div className="tutor-heading">
          <h2>Tutor</h2>
          <span className="tutor-status">{tutorStatus(model)}</span>
        </div>
        <div className="message-list" aria-live="polite" ref={messageListRef}>
          {messages.map((message) => (
            <div className={`chat-turn ${message.role}`} key={message.id}>
              <div className={`chat-message ${message.role}`}>
                <p><MathText highlightedText={null} text={message.content} /></p>
              </div>
              <ToolTags tags={message.toolTags} />
            </div>
          ))}
        </div>
        <div className="chat-dock">
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
      </div>
    </aside>
  );
}

function ToolTags({ tags }: { tags?: string[] }) {
  if (!tags?.length) {
    return null;
  }
  const visibleTags = tags.slice(-3);
  const hiddenCount = tags.length - visibleTags.length;
  return (
    <div className="tool-tags" aria-label="Tool calls">
      {hiddenCount > 0 ? <span className="tool-tag tool-tag-muted">+{hiddenCount} earlier</span> : null}
      {visibleTags.map((tag, index) => (
        <span className="tool-tag" key={`${tag}-${index}`}>
          <MathText highlightedText={null} text={tag} />
        </span>
      ))}
    </div>
  );
}

function tutorStatus(model: string | null) {
  if (model) {
    return model === "local-guided-preview" ? "Local guided preview" : `Model: ${model}`;
  }
  return "Model after first turn";
}
