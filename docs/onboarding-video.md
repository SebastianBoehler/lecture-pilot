# Professor onboarding video

The header's **Watch introduction** action opens a native video player beside
clickable chapters. Playback updates the active chapter and its English/German
instructions. The recording and optional captions are English. Chapter selection
seeks without changing whether playback is paused. Closing the dialog stops it.

## Media storage

The edited recording and sidecars are tracked in Git under
`docs/onboarding-media/2026-09-07-r3/`:

- `lecturepilot-onboarding.mp4` (H.264/AAC, faststart)
- `poster.jpg`
- `captions.en.vtt`
- `chapters.vtt`

Vite serves this directory at `/media/onboarding` in development. Production mounts
it read-only into the web container at `/srv/lecturepilot-media`. Nginx serves
correct media types and byte ranges, so the player can seek without downloading
the entire file. Files have immutable caching: publish a new versioned directory
for subsequent edits and update `ONBOARDING_MEDIA` and chapter timestamps in
`apps/web/src/onboardingChapters.ts`. Never replace bytes at an existing URL.

The files are public onboarding assets. Do not place private course uploads,
learner data, credentials, or raw recordings in this directory. Include this
directory in the release checkout; it is separate from course storage and
excluded from Docker build contexts.

Before releasing, verify playback, chapter seeks, captions, media-error feedback,
keyboard dismissal, and the layout in both themes and at a narrow viewport.
Confirm deployed MP4 range requests return HTTP 206 and VTT returns `text/vtt`.

The public **How it works** page also opens the same player from its lecturer
section, so prospective lecturers can watch before signing in.
