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
6. Store the selected candidate and checkpoints in the course workspace.
7. Render the selected video inline in the lesson document, with the outline
   linking to the containing section.

The tutor can explain, pause on, or ask questions about the selected video, but
the harness should decide which videos are visible to the learner. The agent
should not independently browse future or unrelated media while a lesson is in
progress.

Example workspace record:

```json
{
  "videoId": "8NYoQiRANpg",
  "title": "Stanford CS229 kernels video",
  "url": "https://www.youtube.com/watch?v=8NYoQiRANpg",
  "source": "youtube-discovery",
  "query": "kernels feature maps kernel trick machine learning lecture",
  "checkpoints": [
    { "label": "Kernel trick", "seconds": 1736 },
    { "label": "Designing feature vectors", "seconds": 4623 }
  ]
}
```
