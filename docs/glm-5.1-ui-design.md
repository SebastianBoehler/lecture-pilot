# GLM 5.1 UI Design Pass

Generated via OpenRouter model `z-ai/glm-5.1` on 2026-06-05.

## Information Architecture

### Dashboard

- Top bar: logo, search, theme toggle, user menu.
- Main content: course cards with already-unlocked lectures.
- Lecture rows show title, date, attendance status, and an open action.

### Lesson Workspace

- Top bar: back to dashboard, lecture title, provider/storage status, theme toggle.
- Main surface: markdown lesson canvas.
- Right rail: collapsed controls for chat, artifacts, lecture info, and theme.
- Expanded drawer: chat plus artifact tabs.

## Desktop Layout

- Dashboard: centered content with a 960px max width.
- Course cards use a two-column grid on wide screens and a single column below 900px.
- Lesson default: canvas occupies the available width, with a 48px right icon rail.
- Lesson expanded: canvas uses the remaining space, drawer width is clamped between 320px and 420px.
- Highlights render inline in the markdown with a subtle background and left accent border.

## Mobile Layout

- Dashboard becomes a single-column stack.
- Lesson view keeps only back, truncated title, and chat/artifact toggle in the top bar.
- Chat and artifacts open as a bottom sheet above the canvas.

## Light Theme

```css
--color-bg-primary: #ffffff;
--color-bg-secondary: #f6f8fa;
--color-bg-tertiary: #edf0f3;
--color-border-primary: #d8dee4;
--color-border-focus: #0a58ca;
--color-text-primary: #1a1d21;
--color-text-secondary: #57606a;
--color-text-tertiary: #6e7781;
--color-accent-primary: #0a58ca;
--color-accent-hover: #0846b4;
--color-highlight-bg: #fff8c5;
--color-highlight-border: #e3b34c;
--color-danger: #cf222e;
```

## Dark Theme

```css
--color-bg-primary: #0d1117;
--color-bg-secondary: #161b22;
--color-bg-tertiary: #21262d;
--color-border-primary: #30363d;
--color-border-focus: #3b8bf0;
--color-text-primary: #e6edf3;
--color-text-secondary: #8b949e;
--color-text-tertiary: #6e7681;
--color-accent-primary: #3b8bf0;
--color-accent-hover: #58a6ff;
--color-highlight-bg: #3b2e00;
--color-highlight-border: #9e6a03;
--color-danger: #f85149;
```

## Tokens

- Font: `Inter`, system sans-serif.
- Mono font: `JetBrains Mono`, `Cascadia Code`, monospace.
- Sizes: 12, 14, 16, 20, 24px.
- Spacing: 4, 8, 12, 16, 24, 32, 48px.
- Radius: 4, 6, 8px.
- Borders: 1px default, 2px focus.
- Motion: 120ms for controls, 200ms for drawer transitions.

## Component Inventory

- Top bar
- Theme toggle
- Course card
- Lecture row
- Attendance segmented control
- Lesson canvas
- Canvas highlight
- Right icon rail
- Tutor drawer
- Chat bubbles
- Artifact tabs
- Quiz card
- Code card
- Summary card
- Status badge

## Focused Lesson Defaults

Visible by default:

- top bar
- lecture title
- provider/storage status
- full markdown canvas
- inline highlights
- collapsed right rail

Hidden until requested:

- course list
- lecture metadata
- chat thread
- artifact list
- quiz/code/diagram panels

## Demo Copy

- Course: `Grundlagen des Maschinellen Lernens`
- Lecture: `Lecture 03: Kernels and Feature Maps`
- Chat placeholder: `Ask about this lecture...`
- Agent message: `I highlighted the definition that drives the proof. Want a short derivation check?`
- Quiz title: `Quiz: Feature Maps`
- Summary title: `Memory Card`

## React Implementation Checklist

1. Define CSS variables for both themes.
2. Toggle `data-theme` on the document element.
3. Build separate dashboard and lesson states.
4. Keep lecture selection out of the default lesson workspace.
5. Use a collapsible right drawer for chat and artifacts.
6. Use stable `sectionId` and `spanId` values for canvas highlights.
7. Scroll/focus highlights from agent commands.
8. Render artifacts in tabs inside the drawer.
9. Use a bottom sheet on mobile.
10. Keep all controls keyboard accessible.

