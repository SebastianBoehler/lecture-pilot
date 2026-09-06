import { ArrowDown, ChevronRight } from "lucide-react";
import { useLayoutEffect, useRef, useState } from "react";
import { MathText } from "./MathText";
import { LessonDrawerClose } from "./LessonDrawerClose";
import { TutorActivity } from "./TutorActivity";
import { TutorComposer } from "./TutorComposer";
import { useI18n } from "./i18n";
import type { ChatMessage } from "./types";

export function TutorDrawer({
  messages,
  model,
  sessionGoal = null,
  onClose,
  onSendMessage,
}: {
  messages: ChatMessage[];
  model: string | null;
  sessionGoal?: string | null;
  onClose: () => void;
  onSendMessage: (message: string) => Promise<void>;
}) {
  const { t } = useI18n();
  const listRef = useRef<HTMLDivElement>(null);
  const following = useRef(true);
  const [showLatest, setShowLatest] = useState(false);
  const hasPendingTurn = messages.some((message) => message.isPending);
  useLayoutEffect(() => {
    if (following.current && listRef.current)
      listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages]);

  function scrollChanged() {
    const list = listRef.current;
    if (!list) return;
    following.current = list.scrollHeight - list.clientHeight - list.scrollTop < 48;
    setShowLatest(!following.current);
  }
  function jumpToLatest() {
    if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
    following.current = true;
    setShowLatest(false);
  }
  return (
    <aside className="drawer tutor-drawer" id="lesson-panel" aria-label="Tutor drawer">
      <LessonDrawerClose returnFocusId="lesson-panel-trigger-chat" onClose={onClose} />
      <div className="tutor-drawer-section">
        <header className="tutor-heading">
          <h2>{t("chat.title")}</h2>
        </header>
        <details className="tutor-session-details">
          <summary tabIndex={0}>
            <ChevronRight className="disclosure-chevron" size={14} aria-hidden="true" />
            {t("chat.details")}
          </summary>
          {sessionGoal ? (
            <section aria-label={t("tutor.sessionGoal")}>
              <strong>{t("tutor.sessionGoal")}</strong>
              <p>{sessionGoal}</p>
            </section>
          ) : null}
          <p>
            <strong>{t("chat.model")}</strong>
            <span>
              {model === "local-guided-preview"
                ? t("chat.preview")
                : (model ?? t("chat.modelPending"))}
            </span>
          </p>
        </details>
        <div
          className="message-list"
          aria-live="polite"
          aria-label={t("chat.title")}
          ref={listRef}
          onScroll={scrollChanged}
        >
          {messages.map((message) => (
            <div className={`chat-turn ${message.role}`} key={message.id}>
              {message.role === "agent" ? (
                <TutorActivity tags={message.toolTags} pending={message.isPending} />
              ) : null}
              {!message.isPending ? (
                <div className={`chat-message ${message.role}`}>
                  <span className="chat-speaker">
                    {t(message.role === "user" ? "chat.you" : "chat.title")}
                  </span>
                  <div className="chat-message-content">
                    <MathText highlightedText={null} mode="block" text={message.content} />
                  </div>
                </div>
              ) : null}
            </div>
          ))}
        </div>
        <div className="tutor-composer-dock">
          {showLatest ? (
            <button type="button" className="chat-latest" onClick={jumpToLatest}>
              <ArrowDown size={14} aria-hidden="true" />
              {t("chat.latest")}
            </button>
          ) : null}
          <TutorComposer pending={hasPendingTurn} onSendMessage={onSendMessage} />
        </div>
      </div>
    </aside>
  );
}
