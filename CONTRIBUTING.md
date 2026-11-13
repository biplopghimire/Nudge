# Contributing

## Branch names

```
<type>/<issue>-<short-slug>
```

- `type` is one of `feat`, `fix`, `chore`, `docs`, `test`, `refactor`.
- `issue` is the GitHub issue number. Leave it out (`<type>/<short-slug>`) only when there is no issue.
- `short-slug` is 2–5 lowercase words joined by hyphens.

Examples: `fix/59-signup-field-errors`, `feat/10-auto-title-chats`, `chore/gcloudignore`.

## Pull request titles

```
<type>: <What the change does, in plain words> (#<issue>)
```

- Same `type` as the branch, lowercase, followed by a colon.
- Start the description with a capital letter and an imperative verb ("Show", "Add", "Stop"), no trailing period.
- End with the issue number in parentheses when there is one.
- Put `Fixes #<issue>` in the PR description so merging closes the issue.

Examples:

- `fix: Show sign-up errors for a bad email or short password (#59)`
- `feat: Name new chats after their first message (#10)`
- `chore: Keep .env and .venv out of Cloud Run source uploads`
