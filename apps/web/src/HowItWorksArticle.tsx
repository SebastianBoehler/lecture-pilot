import { useI18n } from "./i18n";
import { InfoArticle } from "./InfoArticle";
import { howItWorksContent } from "./howItWorksContent";
import { OnboardingVideo } from "./OnboardingVideo";

export function HowItWorksArticle() {
  const { locale } = useI18n();
  const de = locale === "de";
  return (
    <InfoArticle
      content={howItWorksContent[locale]}
      afterSection={{
        lecturers: (
          <div className="guide-video">
            <OnboardingVideo />
            <span>
              {de
                ? "Einführung: Kurserstellung und Studierendenansicht, mit Kapiteln"
                : "Watch the chaptered introduction: course setup and student experience"}
            </span>
          </div>
        ),
        behind: (
          <figure className="guide-workspace">
            <div>
              <strong>
                {de
                  ? "Gemeinsamer Kurs · für den Tutor schreibgeschützt"
                  : "Shared course · read-only for the tutor"}
              </strong>
              <p>
                {de
                  ? "Quellen → bestätigte Lernziele → veröffentlichte Vorlesungen"
                  : "Sources → approved learning goals → published lectures"}
              </p>
            </div>
            <div>
              <strong>
                {de ? "+ Dein privater Lernworkspace" : "+ Your private learner workspace"}
              </strong>
              <p>
                {de
                  ? "Versuche · Annotationen · eigene Abschnitte · Kurserinnerungen"
                  : "Attempts · annotations · personal sections · course memory"}
              </p>
            </div>
            <div>
              <strong>
                {de ? "+ Deine kursübergreifenden Vorlieben" : "+ Your cross-course preferences"}
              </strong>
              <p>
                {de
                  ? "Im Profil einsehbare und entfernbare Erinnerungen"
                  : "Saved memory you can inspect and remove in your profile"}
              </p>
            </div>
            <figcaption>
              {de
                ? "Zusammen bilden sie den erlaubten Kontext für den Tutor. Dateien bleiben in getrennten Bereichen; es entsteht kein eigener Server pro Person."
                : "Together these form the tutor’s permitted context. Files stay in separate areas; this does not create a separate server for each person."}
            </figcaption>
          </figure>
        ),
      }}
    />
  );
}
