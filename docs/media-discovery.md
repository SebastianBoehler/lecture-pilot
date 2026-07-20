# Media discovery

LecturePilot treats external media as professor-reviewed course assets, not as
free-form model browsing during a tutor turn.

The discovery contract mirrors the practical `learning-app` pipeline:

1. Build a search query from the course title, lecture title, section heading,
   and learning goal.
2. Fetch YouTube candidates through the YouTube Data API when `YOUTUBE_API_KEY`
   is configured.
3. Normalize each candidate into stable metadata: `videoId`, title, channel,
   duration, language, view count, URL, thumbnail, and description.
4. Reject shorts and videos shorter than the configured minimum duration.
5. Rank remaining candidates by term overlap, preferred language, duration fit,
   and view count.
6. Store the professor-approved candidate in the course workspace.
7. Render the selected video inline in the lesson document, with the outline
   linking to the containing section.

Implemented admin endpoints:

```http
GET /admin/courses/{course_id}/media/youtube/search?q=bayesian+decision+theory
```

The search route uses the YouTube Data API when `YOUTUBE_API_KEY` is set. It
normalizes `search.list` results through `videos.list`, rejects shorts and tiny
clips, then ranks by term overlap, duration fit, and view count. The current
database session must own the exact course; development identity headers exist
only when explicitly enabled locally.

```http
POST /admin/courses/{course_id}/lectures/{lecture_id}/media/youtube
Content-Type: application/json
```

Body:

```json
{
  "section_id": "bayes-formula",
  "video": {
    "video_id": "selected-id",
    "title": "Bayesian Decision Theory",
    "channel_title": "ML Course",
    "url": "https://www.youtube.com/watch?v=selected-id"
  }
}
```

Approved selections are stored under the persistent course workspace at
`courses/<tenant>/<course>/canvas/media/` and merged into the selected section
as `video` blocks. Search candidates are transient; only an explicit owner
selection becomes course state. Students see that selection only through a
published and unlocked canvas.

The tutor can explain or ask questions about a visible approved video. It does
not receive a general browser or YouTube-search tool and cannot independently
add future or unrelated media during a learner turn.

Example workspace record:

```json
{
  "block_id": "youtube-selected-video-id",
  "section_id": "bayes-formula",
  "approved_by": "<internal-user-id>",
  "approved_at": "2026-07-20T10:00:00+00:00",
  "note": null,
  "video": {
    "video_id": "selected-video-id",
    "title": "Naive Bayes classifier lecture",
    "channel_title": "ML Course",
    "url": "https://www.youtube.com/watch?v=selected-video-id"
  }
}
```
