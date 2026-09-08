# Student browser tools (WebMCP)

LecturePilot registers two public tools in every open tab, plus seven student tools
while a student is signed in.
They support navigation, display settings and bounded read-only learning context.
The human student owns the learning interaction.

Public tools require no sign-in and make no account API requests:

- `lecturepilot_get_public_information`: accepts optional `page` (`how-it-works`,
  `learning-science`, `privacy`) and `language` (`en`, `de`). Returns the existing
  public guide and links to the other guides.
- `lecturepilot_open_public_page`: accepts a required allowlisted `page` and opens
  that guide. It respects the same active-learning navigation guard.

Each student invocation first verifies the session through `/me`. Expired sessions,
changed identities, non-student accounts and revoked course access fail closed,
including browser-only tools. Course listings use the server-verified course list.
Local demo sessions expose only public tools: development headers are not an
authenticated student session. Production authentication is enforced by the backend.

The production build emits readable HTML for the three public guides, with matching
descriptions and WebPage structured data. React takes over the same public content
when JavaScript runs; metadata follows page and language changes. `llms.txt` is a
small index generated from the same guides for agents that support that convention.
It is not an SEO ranking promise. No learner data or course sources enter these files.
`publicInformation.ts` owns the shared catalogue; `tooling/publicDiscovery.ts` owns
build output, and `usePublicMetadata.ts` updates metadata during app navigation.

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
out and verify that only the two public tools remain. Never submit learning work as a smoke test.

Implementation: `webMcpTools.ts` owns the allowlist and data projections;
`useWebMcp.ts` owns browser registration; `App.tsx` supplies existing UI actions.
