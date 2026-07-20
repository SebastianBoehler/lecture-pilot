# Workspace Package

This is a reserved package boundary, not a published or imported package. The
current filesystem-like API is implemented in
`apps/api/src/lecturepilot/workspace*.py`, `storage_layout.py`, and
`canvas_workspace.py`.

Local development uses `.lecturepilot/`; production Compose mounts a persistent
volume at `/app/storage`. An object-storage adapter is not implemented. Any
future adapter must preserve the same typed policy, capability, ownership, and
authenticated asset-serving boundaries.
