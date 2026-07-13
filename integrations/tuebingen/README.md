# Tübingen Integration

This package will adapt `tue-api-wrapper` responses into LecturePilot course,
lecture, attendance, and material records.

Initial responsibilities:

- authenticated Alma timetable title lookup without per-course detail enrichment
- course matching
- lecture date extraction
- ILIAS/Moodle material discovery
- safe session storage handoff to the backend
- parallel post-login Alma/ILIAS synchronization with persisted loading/error state
