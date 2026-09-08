# Student browser tools (WebMCP)

LecturePilot registers seven tools while a student is signed in to an open tab.
They support navigation, display settings and bounded read-only learning context.
The human student owns the learning interaction.

| Tool prefix: `lecturepilot_` | Input                              | Result or action                                                                                  |
| ---------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------- |
| `list_courses`               | none                               | Authorized course IDs, titles, instructors and terms                                              |
| `get_course_context`         | `course_id`                        | Course metadata and released, unlocked, published lecture metadata                                |
| `get_learning_progress`      | `course_id`, optional `lecture_id` | Passed lecture IDs, or publication-bound gate statuses and supported/independent/delayed evidence |
| `open_course`                | `course_id`                        | Select the course workspace                                                                       |
| `open_lecture`               | `course_id`, `lecture_id`          | Navigate to the released learner lecture                                                          |
| `get_display_settings`       | none                               | Current interface theme and language                                                              |
| `set_display_settings`       | `theme` and/or `language`          | Set light/dark theme or en/de interface language                                                  |

There is no overall learner ability score. Evidence flags describe recorded work,
not a claim of mastery. Tool output excludes answer text, pending assessment
prompts, quiz responses, hidden tasks, source files, memory, credentials and chat.
Course context currently means metadata, not lecture teaching content.

No tools submit answers, change attendance, pass gates, request support, send tutor
messages, generate exams, change teaching preferences, or manage professor content.
Navigation refuses to interrupt a pending tutor response or focused assessment.
Opening a lecture requests navigation; ordinary UI loading and error handling
still determine whether its canvas loads successfully.

## Browser and agent requirements

The implementation targets the
[4 September 2026 WebMCP draft](https://webmachinelearning.github.io/webmcp/):
`document.modelContext.registerTool(tool, { signal })`. Registration is removed by
aborting its signal on logout, session replacement or unmount. An in-flight result
is discarded if the active session changes. Partial registration failure removes
all this integration's tools and shows an error.

WebMCP is an experimental browser API, not a remote MCP server. A supporting
browser/agent integration must discover and invoke tools in the open tab. Adding
this feature does not automatically connect every Codex or Claude Code client.
There is no polyfill, extension installation, remote endpoint, or deprecated
`navigator.modelContext` compatibility path. Unsupported browsers keep the normal
UI and register no tools. HTTPS (or trustworthy localhost) is required by the API.

Tools reuse existing authenticated read APIs; backend course access, release and
publication checks remain authoritative. Inputs are validated again at execution,
and returned objects use explicit field allowlists. Course-authored text is marked
untrusted. No additional cross-origin exposure is requested.

These restrictions describe the offered tools. They cannot prove a human operated
the ordinary UI or stop a general browser agent from clicking other visible controls.

## Verification

Run `npm run test --workspace apps/web -- src/webMcpTools.test.ts src/useWebMcp.test.ts`
for input/access boundaries, progress redaction, navigation and registration lifecycle.
In a supporting browser, sign in to a local student session and discover the seven
tools. Call display settings and navigation tools, inspect the actual UI, then log
out and verify that tool discovery is empty. Never submit learning work as a smoke test.

Implementation: `webMcpTools.ts` owns the allowlist and data projections;
`useWebMcp.ts` owns browser registration; `App.tsx` supplies existing UI actions.
