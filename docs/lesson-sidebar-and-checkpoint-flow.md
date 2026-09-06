# Sidebar width and assessment flow

The desktop learning workspace has a small resize grip centered on the navigation
rail's left border. It overlays the boundary and occupies no layout column.
Dragging it resizes the rail and active panel together. The content panel is at
least 320px wide; total sidebar width ranges from 376px to 720px, capped to leave
400px for the canvas. Arrow keys change width by 20px;
Home/End reach the bounds; double-click restores the default 436px total width.
The width is shared across panel modes for the mounted workspace. At 860px and
below, the existing bottom-sheet layout applies and the separator is hidden.
`LessonSidebarResize` owns sizing and pointer/keyboard handling; `LessonWorkspace`
provides the layout element and renders it only when learning materials are open.

New authoring guidance discourages redundant adjacent optional assessments and
asks for useful explanations or transitions between formative checks. For multiple
approved diagnostics in one section, the writer can mark a neutral orientation:

```markdown
<!-- block id="check-context-t2" type="paragraph" -->

The next task asks you to justify the comparison you make.
```

The suffix is the assigned practice target ID. Checkpoint assembly places this
paragraph immediately before `practice-t2`, preserving approved diagnostic order,
exact task text and IDs. Substantive teaching follows the diagnostic group. Existing
sections without orientation markers still assemble; published canvases are not
rewritten. Invalid or duplicate orientation markers fail validation. Writers and
critics are instructed to keep orientation free of answers and hints; a paragraph's
semantic quality still requires review, not just structural validation.

Verification: pointer and keyboard resize tests, window clamping, existing lesson
flow/accessibility tests, and checkpoint assembly/prompt tests. Desktop browser
checks confirmed width changes across panel modes, minimum/maximum bounds and
retained canvas space without horizontal overflow. No new provider-generated
canvas or regeneration of private published course material was performed.
