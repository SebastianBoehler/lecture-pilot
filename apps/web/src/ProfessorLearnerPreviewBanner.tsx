import { Eye } from "lucide-react";

import { useI18n } from "./i18n";

export function ProfessorLearnerPreviewBanner({ onBack }: { onBack: () => void }) {
  const { t } = useI18n();
  return (
    <aside className="professor-preview-banner" aria-label={t("professor.preview.bannerTitle")}>
      <Eye aria-hidden="true" size={18} />
      <div>
        <strong>{t("professor.preview.bannerTitle")}</strong>
        <span>{t("professor.preview.bannerHelp")}</span>
      </div>
      <button className="ghost-button" type="button" onClick={onBack}>
        {t("professor.preview.back")}
      </button>
    </aside>
  );
}
