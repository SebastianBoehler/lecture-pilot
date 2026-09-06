import { ChevronRight } from "lucide-react";
import { useI18n } from "./i18n";
import type { MessageKey } from "./i18nMessages";

const labels: Record<string, MessageKey> = {
  read: "chat.read",
  find: "chat.search",
  grep: "chat.search",
  focus: "chat.focus",
  highlight: "chat.highlight",
  phrase: "chat.phrase",
  write: "chat.write",
  edit: "chat.write",
  canvas: "chat.write",
  generate_image: "chat.image",
  remember: "chat.memory",
  gate: "chat.gate",
  record_gate: "chat.gate",
  artifact: "chat.artifact",
  ls: "chat.list",
  pwd: "chat.list",
};

export function TutorActivity({
  tags = [],
  pending = false,
}: {
  tags?: string[];
  pending?: boolean;
}) {
  const { t } = useI18n();
  if (!tags.length)
    return pending ? (
      <p className="tutor-working" role="status">
        {t("chat.working")}
      </p>
    ) : null;
  const count = t(tags.length === 1 ? "chat.action" : "chat.actions", { count: tags.length });
  return (
    <div className="tutor-activity" aria-label={t("chat.activity")}>
      <details className="tool-timeline">
        <summary tabIndex={0}>
          <ChevronRight className="disclosure-chevron" size={14} aria-hidden="true" />
          {pending ? (
            <span role="status" className="tutor-working">
              {t("chat.working")}
            </span>
          ) : null}
          <span>{count}</span>
        </summary>
        <ol>
          {tags.map((tag, index) => {
            const separator = tag.indexOf(":");
            const name = separator < 0 ? tag : tag.slice(0, separator);
            const target = separator < 0 ? "" : tag.slice(separator + 1).trim();
            return (
              <li key={`${index}-${tag}`}>
                <details className="tool-call">
                  <summary tabIndex={0}>
                    <ChevronRight className="disclosure-chevron" size={12} aria-hidden="true" />
                    <span>{labels[name] ? t(labels[name]) : name}</span>
                    {target ? <code title={target}>{target}</code> : null}
                  </summary>
                  <pre>{tag}</pre>
                </details>
              </li>
            );
          })}
        </ol>
      </details>
    </div>
  );
}
