import { Check, CircleCheck, CircleAlert, Clock3, Eye, LoaderCircle } from "lucide-react";
import { useI18n } from "./i18n";

const states = {
  pending: { icon: Clock3, label: "builder.generate.progressStatus.pending" },
  generating: { icon: LoaderCircle, label: "builder.generate.progressStatus.generating" },
  error: { icon: CircleAlert, label: "builder.generate.progressStatus.error" },
  review: { icon: Eye, label: "builder.generate.reviewStatus.pending" },
  approved: { icon: Check, label: "builder.generate.reviewStatus.approved" },
  published: { icon: CircleCheck, label: "builder.publish.published" },
} as const;

export function GenerationSpinner() {
  return <LoaderCircle aria-hidden="true" className="generation-spinner" size={14} />;
}

export function ProfessorLectureStatus({ state }: { state: keyof typeof states }) {
  const { t } = useI18n();
  const { icon: Icon, label } = states[state];
  return (
    <small className={`lecture-status lecture-status-${state}`} aria-live="polite">
      {state === "generating" ? <GenerationSpinner /> : <Icon aria-hidden="true" size={14} />}
      {t(label)}
    </small>
  );
}
