import { SendHorizontal } from "lucide-react";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";

import { MathText } from "./MathText";
import { LessonDrawerClose } from "./LessonDrawerClose";
import type { ChatMessage } from "./types";

export function TutorDrawer({
  messages,
  model,
  onClose,
  onSendMessage,
}: {
  messages: ChatMessage[];
  model: string | null;
  onClose: () => void;
  onSendMessage: (message: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const messageListRef = useRef<HTMLDivElement>(null);
  const hasPendingTurn = messages.some((message) => message.isPending);

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
    <aside className="drawer tutor-drawer" id="lesson-panel" aria-label="Tutor drawer">
      <LessonDrawerClose returnFocusId="lesson-panel-trigger-chat" onClose={onClose} />
      <div className="drawer-section tutor-drawer-section">
        <div className="tutor-heading">
          <h2>Tutor</h2>
          <span className="tutor-status">{hasPendingTurn ? "Working..." : tutorStatus(model)}</span>
        </div>
        <div className="message-list" aria-live="polite" ref={messageListRef}>
          {messages.map((message) => (
            <div className={`chat-turn ${message.role}`} key={message.id}>
              {message.role === "agent" ? <ToolTags tags={message.toolTags} /> : null}
              <div
                aria-busy={message.isPending ? "true" : undefined}
                className={["chat-message", message.role, message.isPending ? "is-pending" : ""]
                  .filter(Boolean)
                  .join(" ")}
              >
                <div className="chat-message-content">
                  <MathText highlightedText={null} mode="block" text={message.content} />
                </div>
              </div>
              {message.role === "user" ? <ToolTags tags={message.toolTags} /> : null}
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
  const hiddenTags = tags.slice(0, -3);
  return (
    <div className="tool-tags" aria-label="Tool calls">
      {hiddenTags.length > 0 ? (
        <details className="tool-history">
          <summary>+{hiddenTags.length} earlier</summary>
          <div className="tool-history-list">
            {hiddenTags.map((tag, index) => (
              <span className={toolTagClassName(tag)} key={`${tag}-${index}`}>
                <MathText highlightedText={null} text={tag} />
              </span>
            ))}
          </div>
        </details>
      ) : null}
      {visibleTags.map((tag, index) => (
        <span className={toolTagClassName(tag)} key={`${tag}-${index}`}>
          <MathText highlightedText={null} text={tag} />
        </span>
      ))}
    </div>
  );
}

function toolTagClassName(tag: string) {
  return ["tool-tag", tag.startsWith("phrase:") ? "tool-tag-detail" : ""].filter(Boolean).join(" ");
}

function tutorStatus(model: string | null) {
  if (model) {
    return model === "local-guided-preview" ? "Local guided preview" : `Model: ${model}`;
  }
  return "Model after first turn";
}
