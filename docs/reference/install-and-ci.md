# Install and CI guide

How `icansee` actually wires itself into a project, what each layer
catches, and how to translate the GitHub Actions workflow to other CI
providers.

## What gets installed

Running `scripts/install.sh` from inside a git repo:

1. **Detects** the project's framework(s) from `package.json` deps and
   filesystem hints. Supports React, Next.js, Solid, Preact, Vue, Nuxt,
   Svelte, SvelteKit, Angular, Astro, and plain HTML. Multiple are
   fine. Monorepos get all their relevant configs.
2. **Installs** the matching ESLint plugin(s) as devDependencies via
   your project's package manager (npm, pnpm, yarn, or bun, detected
   from lockfile).
3. **Drops flat-config files** into `.icansee/` (one per framework).
   These reference the user's installed plugins.
4. **Wires the pre-commit hook** into `.husky/pre-commit` if husky is
   already set up; otherwise into `.git/hooks/pre-commit`. The hook
   calls `audit.sh --staged` on every commit (~1–3s).
5. **Wires the pre-push hook** (same husky/.git decision). Calls
   `rendered_audit.sh`, which builds the project, serves it, and runs
   `@axe-core/cli` against every route in `.icansee/routes.json`. Skips
   itself when only docs, `.github/`, or `.icansee/` files are in the
   push. Around 30 to 90 seconds per push.
6. **Copies the GitHub Actions workflow** to
   `.github/workflows/a11y.yml` and creates `.icansee/routes.json`
   listing the routes axe-core will scan.

Opt-out flags: `--no-hook`, `--no-pre-push`, `--no-ci`. All three layers
are on by default since each catches a class of issue the others don't.

## What each layer catches

| Layer        | When it runs        | Speed     | What it catches                                                                                  | What it misses                                                                  |
| ------------ | ------------------- | --------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| Pre-commit   | Every `git commit`  | ~1–3s     | Static source violations on staged files: missing alt, no label, bad ARIA, palette token failures. | Computed contrast through CSS cascade, focus state, anything tied to rendered DOM. |
| Pre-push     | Every `git push`    | ~30–90s   | Everything axe-core checks against the built and served site: computed contrast, landmark coverage, focus state. Same engine as Vercel toolbar. | UI states reachable only by interaction (hover, open dialog). Vercel's "record" mode covers these manually. |
| CI (axe-core)| Every PR or push    | ~1–5min   | Same as pre-push, but enforced at merge boundary where `--no-verify` cannot help.                | Same as pre-push.                                                               |

The three layers are complementary, not redundant.

- Pre-commit gives instant feedback while authoring code.
- Pre-push closes the rendered-DOM gap before the code leaves your
  machine, without slowing every commit.
- CI catches the case where someone bypassed pre-push with
  `--no-verify`.

## Configuring the pre-push (rendered) layer

The pre-push hook calls `rendered_audit.sh`, which:

1. Pre-flights for a Chrome-class browser (Chrome or Chromium). Exits
   with a clear error if missing.
2. Builds the project (auto-detects `npm run build`; skips if no build
   script).
3. Starts the app (auto-detects `npm start` or `npm run preview`, falls
   back to `npx serve`).
4. Waits for the server to come up.
5. Runs `@axe-core/cli --tags wcag2a,wcag2aa,wcag21a,wcag21aa` against
   each route in `.icansee/routes.json`.
6. Kills the server and exits non-zero on any finding.

Override defaults via env vars or `.icansee/env`:

```bash
# .icansee/env
BUILD_CMD="pnpm build"
SERVE_CMD="pnpm start"
BASE_URL="http://localhost:5173"
WAIT_TIMEOUT=120000
```

Set `BUILD_CMD=""` to skip the build entirely (useful for static-HTML
projects).

### Chrome dependency

`@axe-core/cli` runs axe-core inside headless Chrome via ChromeDriver.
That means the rendered layer needs a Chrome-class browser installed on
the machine where it runs (your laptop for pre-push, the CI runner for
the workflow).

Install one of the following, then re-run:

```bash
# macOS (signed, passes Gatekeeper)
brew install --cask google-chrome

# Linux (Debian/Ubuntu)
sudo apt-get install -y google-chrome-stable
```

The CI workflow's `actions/setup-node@v4` runner already includes
Chrome; no extra step needed there.

### ChromeDriver / Chrome version sync

ChromeDriver and Chrome have to match major versions. When Chrome
auto-updates, ChromeDriver lags briefly. If the rendered audit fails
with `This version of ChromeDriver only supports Chrome version N`, sync
them:

```bash
npx browser-driver-manager install chrome
```

Or pin to a specific major:

```bash
npx browser-driver-manager install chrome@147
```

Or pass an explicit driver path to axe:

```bash
npx @axe-core/cli <url> --chromedriver-path /path/to/chromedriver
```

`rendered_audit.sh` detects this exact failure mode and exits with code
2 (infrastructure error, not a real a11y finding) and a one-line hint
pointing here.

## When to opt out of pre-push

Use `install.sh --no-pre-push` if any of these apply:

- Build is over 3 minutes. Pre-push will feel punishing. Rely on CI;
  the pre-commit layer still catches most issues locally.
- You push very frequently to share work-in-progress branches. The hook
  fires on every push including draft branches. CI on the PR is
  enough.
- No reliable local server. If the app needs prod env vars, secrets, or
  a backing service that's not available on the dev machine,
  rendered_audit.sh won't be able to start it.

You can always re-enable later with `install.sh` (no flag). Install is
idempotent.

## Translating the GH Actions workflow to other CI providers

The workflow's job is straightforward: install deps, build, start the
app, run `@axe-core/cli` against routes from `.icansee/routes.json`.
The shell logic transfers directly. Map the YAML wrapper to your
provider.

### GitLab CI (`.gitlab-ci.yml`)

```yaml
a11y:
  image: node:20
  before_script:
    - apt-get update && apt-get install -y python3
  script:
    - npm ci
    - npm run build
    - SERVE_CMD="${SERVE_CMD:-npm start}"
    - $SERVE_CMD &
    - npx --yes wait-on "${BASE_URL:-http://localhost:3000}" --timeout 60000
    - |
      ROUTES=$(cat .icansee/routes.json | python3 -c 'import json,sys; print(" ".join(json.load(sys.stdin)))')
      for r in $ROUTES; do
        npx --yes @axe-core/cli "${BASE_URL:-http://localhost:3000}$r" \
          --tags wcag2a,wcag2aa,wcag21a,wcag21aa --exit
      done
```

### CircleCI (`.circleci/config.yml`)

```yaml
jobs:
  a11y:
    docker: [ image: cimg/node:20.0 ]
    steps:
      - checkout
      - run: npm ci
      - run: npm run build
      - run:
          name: Run axe-core
          command: |
            ${SERVE_CMD:-npm start} &
            npx --yes wait-on "${BASE_URL:-http://localhost:3000}" --timeout 60000
            ROUTES=$(cat .icansee/routes.json | python3 -c 'import json,sys; print(" ".join(json.load(sys.stdin)))')
            for r in $ROUTES; do
              npx --yes @axe-core/cli "${BASE_URL:-http://localhost:3000}$r" \
                --tags wcag2a,wcag2aa,wcag21a,wcag21aa --exit
            done
```

### Vercel (Build and Deployment Checks)

Vercel runs the toolbar's audit on preview deploys directly. The
`Accessibility Audit` permission must be granted to the project. No CI
workflow needed for the same coverage; the pre-commit gate still
applies locally.

### Bitbucket Pipelines

Same shape, in `bitbucket-pipelines.yml` with the same script body.

## Configuring routes

`.icansee/routes.json` is a JSON array of paths to scan:

```json
["/", "/about", "/dashboard", "/settings"]
```

Add the routes that represent meaningful UI surface. Each one is run
through axe-core; failures from any route block the PR.

## Authenticated routes

`@axe-core/cli` does not handle login flows on its own. Two options:

1. **Test the unauthenticated shell only**: the marketing surface,
   sign-in and sign-up pages. Often enough for the rules that are most
   commonly broken (contrast, labels, headings).
2. **Switch to a Playwright + axe runner** for authenticated routes.
   Skip `@axe-core/cli` and run `@axe-core/playwright` from a
   Playwright spec that signs in first. The skill ships
   `@axe-core/cli` as the default because it's the closest analog to
   Vercel's toolbar; switch when you outgrow it.

## Slow builds

The CI layer requires a build. If your build is over 5 minutes, the
pre-commit gate is doing most of the catching anyway. Two options:

1. **Run CI a11y on a schedule** instead of every PR (nightly, for
   instance).
2. **Build a small a11y-only fixture** that mounts your design system
   on a single page and run axe against just that. Most contrast and
   ARIA issues live in components, not in route-specific layout.

## Bypassing the pre-commit gate

`git commit --no-verify` skips the hook. Use it when:

- The CI layer is going to catch it anyway and you need to land a
  hotfix.
- You're committing an intentional WIP on a branch you'll squash before
  merge.

CI does not honor `--no-verify`. That's by design.

## Updating the skill or changing rules

Re-run `scripts/install.sh` after pulling a new skill version. It will
overwrite `.icansee/eslint-*.config.mjs` and
`.github/workflows/a11y.yml` with the latest templates. Hand-edits to
those files will be lost. Keep custom rules in your own ESLint config,
which the icansee gate doesn't touch.

## What the gate does NOT do

- It does not auto-fix. Findings include suggested fixes (in the
  per-rule remediation patterns) but applying them is the user's call.
- It does not check authoring tools that don't produce one of the
  supported source formats. Templating dialects (Pug, Handlebars, EJS)
  ride on the CI layer's rendered-DOM check.
- It does not replace manual testing with assistive tech. Pass the
  gate, then still do a screen-reader pass on flagship flows before
  launch.
