import { useId, useRef, useState } from "react";
import { PlayCircle, X } from "lucide-react";

import { useI18n } from "./i18n";
import { ONBOARDING_MEDIA, onboardingChapters } from "./onboardingChapters";
import { useModalDialog } from "./useModalDialog";
import "./onboarding-video.css";

export function OnboardingVideo() {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const label = t("onboardingVideo.open");
  return (
    <>
      <button
        className="top-icon-button"
        type="button"
        aria-label={label}
        title={label}
        onClick={() => setOpen(true)}
      >
        <PlayCircle size={17} />
      </button>
      {open && <OnboardingDialog onClose={() => setOpen(false)} />}
    </>
  );
}

function OnboardingDialog({ onClose }: { onClose: () => void }) {
  const { locale, t } = useI18n();
  const chapters = onboardingChapters(locale);
  const dialog = useModalDialog();
  const video = useRef<HTMLVideoElement>(null);
  const titleId = useId();
  const [time, setTime] = useState(0);
  const [error, setError] = useState(false);
  const active = Math.max(0, chapters.filter((chapter) => chapter.start <= time).length - 1);
  const chapter = chapters[active];
  function seek(start: number) {
    if (!video.current) return;
    video.current.currentTime = start;
    setTime(start);
  }
  return (
    <dialog
      ref={dialog}
      className="onboarding-video-dialog"
      aria-labelledby={titleId}
      aria-modal="true"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <header className="onboarding-video-header">
        <div>
          <h2 id={titleId}>{t("onboardingVideo.title")}</h2>
          <p>{t("onboardingVideo.subtitle")}</p>
        </div>
        <button
          className="top-icon-button"
          type="button"
          aria-label={t("onboardingVideo.close")}
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </header>
      <div className="onboarding-video-layout">
        <div className="onboarding-video-player">
          <video
            ref={video}
            aria-label={t("onboardingVideo.video")}
            controls
            playsInline
            preload="metadata"
            poster={`${ONBOARDING_MEDIA}/poster.jpg`}
            onTimeUpdate={(event) => setTime(event.currentTarget.currentTime)}
            onError={() => setError(true)}
          >
            <source src={`${ONBOARDING_MEDIA}/lecturepilot-onboarding.mp4`} type="video/mp4" />
            <track
              kind="captions"
              src={`${ONBOARDING_MEDIA}/captions.en.vtt`}
              srcLang="en"
              label="English"
            />
            <track
              kind="chapters"
              src={`${ONBOARDING_MEDIA}/chapters.vtt`}
              srcLang="en"
              label="Chapters"
            />
          </video>
          {error && <p role="alert">{t("onboardingVideo.loadFailed")}</p>}
          <section className="onboarding-video-description" aria-label={chapter.title}>
            <h3>{chapter.title}</h3>
            <ul>
              <li>{chapter.action}</li>
              <li>{chapter.result}</li>
            </ul>
          </section>
        </div>
        <nav className="onboarding-video-chapters" aria-label={t("onboardingVideo.chapters")}>
          {chapters.map((item, index) => (
            <button
              key={item.start}
              type="button"
              aria-current={index === active ? "step" : undefined}
              onClick={() => seek(item.start)}
            >
              <span>
                {Math.floor(item.start / 60)}:{String(Math.floor(item.start % 60)).padStart(2, "0")}
              </span>
              {item.title}
            </button>
          ))}
        </nav>
      </div>
    </dialog>
  );
}
