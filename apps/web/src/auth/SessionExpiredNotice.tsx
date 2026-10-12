import { useI18n } from "../i18n/i18n";

export function SessionExpiredNotice({ onSignIn }: { onSignIn: () => void }) {
  const { t } = useI18n();
  return (
    <p className="form-error session-expired" role="alert">
      {t("session.expired")}{" "}
      <button className="primary-action" type="button" onClick={onSignIn}>
        {t("session.signInAgain")}
      </button>
    </p>
  );
}
