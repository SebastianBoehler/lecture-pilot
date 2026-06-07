# Media Discovery

LecturePilot should treat external media as course workspace pre-assets, not as
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
X-Tenant-Id: tenant-tuebingen
X-User-Id: prof01
X-User-Role: professor
```

The search route uses the YouTube Data API when `YOUTUBE_API_KEY` is set. It
normalizes `search.list` results through `videos.list`, rejects shorts and tiny
clips, then ranks by term overlap, duration fit, and view count.

```http
POST /admin/courses/{course_id}/lectures/{lecture_id}/media/youtube
X-Tenant-Id: tenant-tuebingen
X-User-Id: prof01
X-User-Role: professor
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

Approved selections are stored under
`local-course-materials/<course>/canvas/media/` and merged into the returned
canvas as `video` blocks. The professor can stage candidates without exposing
them to students until they approve a selection.

The tutor can explain, pause on, or ask questions about the selected video, but
the harness should decide which videos are visible to the learner. The agent
should not independently browse future or unrelated media while a lesson is in
progress.

Example workspace record:

```json
{
  "video_id": "selected-video-id",
  "title": "Naive Bayes classifier lecture",
  "channel_title": "ML Course",
  "url": "https://www.youtube.com/watch?v=selected-video-id",
  "source": "youtube-discovery",
  "query": "Bayesian decision theory Naive Bayes classifier lecture",
  "checkpoints": [
    { "label": "Bayes rule", "seconds": 420 },
    { "label": "Classification decision", "seconds": 980 }
  ]
}
```
