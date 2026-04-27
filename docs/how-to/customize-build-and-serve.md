# How to customize build and serve commands

The rendered audit (pre-push and CI) auto-detects how to build and serve
your project. The defaults work for most npm projects, but you can override
any of them.

## Quick reference

The audit reads three values, in order of precedence:

1. Shell environment variables.
2. `.icansee/env` file in the repo root.
3. Auto-detection from `package.json`.

| Variable      | Default                                                 | What it does                              |
| ------------- | ------------------------------------------------------- | ----------------------------------------- |
| `BUILD_CMD`   | `npm run build` if a build script exists, else empty    | Command to build the project              |
| `SERVE_CMD`   | `npm start`, then `npm run preview`, then `npx serve`   | Command to start the app                  |
| `BASE_URL`    | `http://localhost:3000`                                 | Where the served app listens              |
| `WAIT_TIMEOUT`| `60000`                                                  | Milliseconds to wait for server readiness |

## Set per-repo defaults via `.icansee/env`

Create `.icansee/env` and put the values in there. Plain shell syntax, no
quotes around simple values, but quote anything with spaces or special
characters.

```bash
# .icansee/env
BUILD_CMD="pnpm build"
SERVE_CMD="pnpm preview"
BASE_URL="http://localhost:4173"
WAIT_TIMEOUT=120000
```

Commit this file so everyone on the team uses the same commands.

## Override on a single run

For one-off runs without changing the file:

```bash
BASE_URL="http://localhost:5173" \
  ~/.claude/skills/icansee/scripts/rendered_audit.sh
```

This is most useful when debugging a port collision or running against a
pre-built artifact:

```bash
BUILD_CMD="" SERVE_CMD="npx serve -s dist -p 8080" BASE_URL="http://localhost:8080" \
  ~/.claude/skills/icansee/scripts/rendered_audit.sh
```

## Common setups

### Vite project

```bash
BUILD_CMD="npm run build"
SERVE_CMD="npm run preview"
BASE_URL="http://localhost:4173"  # Vite preview default
```

### Next.js production build

```bash
BUILD_CMD="npm run build"
SERVE_CMD="npm start"
BASE_URL="http://localhost:3000"
```

### Next.js dev mode (faster, but see caveat)

```bash
BUILD_CMD=""
SERVE_CMD="npm run dev"
BASE_URL="http://localhost:3000"
```

Caveat: Next.js dev mode adds React-DevTools markup, double-renders in
StrictMode, and extra warning overlays. Findings may differ slightly from
prod.

### Static site (no build step)

```bash
BUILD_CMD=""
SERVE_CMD="npx --yes serve -s public -p 3000"
BASE_URL="http://localhost:3000"
```

### Astro

```bash
BUILD_CMD="npm run build"
SERVE_CMD="npm run preview"
BASE_URL="http://localhost:4321"
```

### SvelteKit

```bash
BUILD_CMD="npm run build"
SERVE_CMD="npm run preview"
BASE_URL="http://localhost:4173"
```

## Set environment for the build itself

If your build needs API keys or feature flags, put them in `.icansee/env`
alongside the icansee variables. Anything in that file is exported into
the audit's shell.

```bash
# .icansee/env
BUILD_CMD="npm run build"
SERVE_CMD="npm start"
NEXT_PUBLIC_API_URL="https://staging.example.com"
ANALYTICS_DISABLED="true"
```

For real secrets, **don't commit `.icansee/env`**. Gitignore it, and let
each developer / CI set their own values.

## Skipping the build entirely

Set `BUILD_CMD=""`. Useful for static-HTML projects or when you've already
built and just want to serve the artifact.

## Verify your overrides

```bash
BUILD_CMD="echo would build" SERVE_CMD="echo would serve" \
  ~/.claude/skills/icansee/scripts/rendered_audit.sh
```

You'll see the placeholder commands echo back, which confirms your env
substitutions are landing where you expect.
