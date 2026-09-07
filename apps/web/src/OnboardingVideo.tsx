import { useId, useLayoutEffect, useRef, useState } from "react";
import { PlayCircle, X } from "lucide-react";

import { useI18n } from "./i18n";
import { ONBOARDING_MEDIA, onboardingChapters } from "./onboardingChapters";
import "./onboarding-video.css";

export function OnboardingVideo() {
  const { locale } = useI18n();
  const [open, setOpen] = useState(false);
  const label = locale === "de" ? "Einführung ansehen" : "Watch introduction";
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
  const { locale } = useI18n();
  const chapters = onboardingChapters(locale);
  const dialog = useRef<HTMLDialogElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const titleId = useId();
  const [time, setTime] = useState(0);
  const [error, setError] = useState(false);
  const active = Math.max(0, chapters.filter((chapter) => chapter.start <= time).length - 1);
  const chapter = chapters[active];
  useLayoutEffect(() => {
    const element = dialog.current!;
    element.showModal();
    return () => element.close();
  }, []);
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
      onCancel={onClose}
    >
      <header className="onboarding-video-header">
        <div>
          <h2 id={titleId}>
            {locale === "de" ? "LecturePilot kennenlernen" : "Getting started with LecturePilot"}
          </h2>
          <p>
            {locale === "de"
              ? "Vom ersten Kurs zur Studierendenansicht · Video auf Englisch"
              : "From your first course to the student experience · English video"}
          </p>
        </div>
        <button
          className="top-icon-button"
          type="button"
          aria-label={locale === "de" ? "Schließen" : "Close"}
          onClick={onClose}
        >
          <X size={20} />
        </button>
      </header>
      <div className="onboarding-video-layout">
        <div className="onboarding-video-player">
          <video
            ref={video}
            aria-label={locale === "de" ? "Einführungsvideo" : "Introduction video"}
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
          {error && (
            <p role="alert">
              {locale === "de"
                ? "Das Video konnte nicht geladen werden. Bitte versuchen Sie es erneut."
                : "The video could not be loaded. Please try again."}
            </p>
          )}
          <section className="onboarding-video-description" aria-label={chapter.title}>
            <h3>{chapter.title}</h3>
            <ul>
              <li>{chapter.action}</li>
              <li>{chapter.result}</li>
            </ul>
          </section>
        </div>
        <nav
          className="onboarding-video-chapters"
          aria-label={locale === "de" ? "Videokapitel" : "Video chapters"}
        >
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
