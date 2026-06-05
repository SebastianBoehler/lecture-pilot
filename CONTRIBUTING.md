# Contributing

This repo should stay small, typed, and test-driven.

## Development Rules

- Write a failing test before behavior changes.
- Keep files under 300 lines where practical.
- Keep provider logic behind the harness contract.
- Do not add mock data as a hidden fallback for production behavior.
- Fail clearly when credentials, provider keys, or course material are missing.
- Keep the frontend focused on the current learning task.

## Verification

Run before opening a pull request:

```bash
pytest apps/api/tests
npm run test --workspace apps/web
npm run build --workspace apps/web
```

