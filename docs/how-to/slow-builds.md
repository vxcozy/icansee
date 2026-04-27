# How to handle a slow build in the rendered audit

The pre-push hook (and the CI workflow) calls `npm run build` by default.
If your build takes more than a few minutes, the pre-push gate becomes
painful and contributors will start reaching for `--no-verify`. Three
mitigation options, ordered by trade-off.

## Option 1: skip the local pre-push, keep CI

Removes the local cost entirely; CI still enforces the rendered audit at
the PR boundary.

```bash
~/.claude/skills/icansee/scripts/install.sh --no-pre-push
```

Re-runs of `install.sh` are idempotent, so you can flip this off and on
freely. Recommended if your build is over 5 minutes.

## Option 2: use a faster build target

Most build pipelines have a "preview" or "dev" mode that's significantly
faster than the production build. Edit `.icansee/env`:

```bash
# .icansee/env
BUILD_CMD="npm run build:fast"
SERVE_CMD="npm run preview"
```

Anything readable by bash works. Keep in mind the audit reports findings
against whatever you build. If your fast build skips Tailwind purging or
PostCSS, your computed contrast numbers may differ from prod.

## Option 3: skip the build, run against the dev server

If your dev server matches prod closely enough (modern Vite, Next.js dev
mode, Astro dev), skip the build:

```bash
# .icansee/env
BUILD_CMD=""
SERVE_CMD="npm run dev"
BASE_URL="http://localhost:5173"
```

Pros: instant pre-push start.
Cons: dev mode often differs from prod (extra warnings, source-mapped CSS,
React StrictMode double-renders that can produce noisy a11y findings). If
you see findings that don't reproduce in prod, that's why.

## Option 4: audit on a schedule instead of every push

Move the rendered check off the per-push critical path entirely:

1. `install.sh --no-pre-push --no-ci` (keep pre-commit).
2. Add a scheduled GitHub Actions workflow that runs the rendered audit
   nightly against your staging environment.
3. Failures open an issue or post to a Slack channel, rather than blocking
   merges.

This is a real shift in posture, from "you can't push broken code" to
"we'll see broken code within a day." Fine for slow-moving codebases.

## Diagnosing a slow build

If the build is slow but you don't know why:

```bash
time npm run build
```

Common culprits:

- Type-checking the entire monorepo (`tsc --noEmit`) when only the app
  needs it. Skip with `--skipLibCheck` or scope to one project.
- Source-map generation in prod mode. Turn off if you don't ship them.
- A separate "build:storybook" or "build:docs" being chained.

A 30-second build at the local pre-push level is fine. A 5-minute build
isn't. Below 30 seconds the gate feels like part of the commit ritual;
above 60 seconds it feels like punishment.
