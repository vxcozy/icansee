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
   the Playwright + `@axe-core/playwright` runner against every
   `route × mode` combination in `.icansee/routes.json`. Skips itself
   when only docs, `.github/`, or `.icansee/` files are in the push.
   Around 30 to 90 seconds per push.
6. **Installs the rendered-audit deps** (`playwright`,
   `@axe-core/playwright`) into `.icansee/node_modules` via a small
   `.icansee/package.json` that the installer manages. Pulls the
   bundled Chromium into Playwright's shared cache
   (`~/Library/Caches/ms-playwright` on macOS,
   `~/.cache/ms-playwright` on Linux). Copies `templates/axe-runner.mjs`
   to `.icansee/axe-runner.mjs`. Keeping these out of your project's
   own `package.json` avoids touching your dep graph and supports
   plain-HTML projects with no root `package.json` at all.
7. **Copies the GitHub Actions workflow** to
   `.github/workflows/a11y.yml` and creates `.icansee/routes.json`
   listing the routes (and color modes) axe-core will scan.

Opt-out flags: `--no-hook`, `--no-pre-push`, `--no-ci`. All three layers
are on by default since each catches a class of issue the others don't.

## What each layer catches

| Layer        | When it runs        | Speed     | What it catches                                                                                  | What it misses                                                                  |
| ------------ | ------------------- | --------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| Pre-commit   | Every `git commit`  | ~1–3s     | Static source violations on staged files: missing alt, no label, bad ARIA, palette token failures. | Computed contrast through CSS cascade, focus state, anything tied to rendered DOM. |
| Pre-push     | Every `git push`    | ~30–90s   | Everything axe-core checks against the built and served site, swept across each configured color mode: computed contrast (light and dark), landmark coverage, focus state. Same engine as Vercel toolbar. | UI states reachable only by interaction (hover, open dialog). Vercel's "record" mode covers these manually. |
| CI (axe-core)| Every PR or push    | ~1–5min   | Same as pre-push, but enforced at merge boundary where `--no-verify` cannot help.                | Same as pre-push.                                                               |

The three layers are complementary, not redundant.

- Pre-commit gives instant feedback while authoring code.
- Pre-push closes the rendered-DOM gap before the code leaves your
  machine, without slowing every commit.
- CI catches the case where someone bypassed pre-push with
  `--no-verify`.

## Configuring the pre-push (rendered) layer

The pre-push hook calls `rendered_audit.sh`, which:

1. Builds the project (auto-detects `npm run build`; skips if no build
   script).
2. Starts the app (auto-detects `npm start` or `npm run preview`, falls
   back to `npx serve`).
3. Waits for the server to come up.
4. Runs `.icansee/axe-runner.mjs` (Playwright + `@axe-core/playwright`)
   for every `route × color-mode` combination in `.icansee/routes.json`,
   with WCAG tags `wcag2a,wcag2aa,wcag21a,wcag21aa`. The runner emulates
   `prefers-color-scheme` per scan so dark-mode contrast is exercised.
5. Kills the server and exits non-zero on any finding.

Playwright bundles its own signed Chromium, so there is no separate
browser install and no ChromeDriver/Chrome version-mismatch class of
failures.

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

### Framework-specific gotchas

Verified against real upstream scaffolds. If you're on one of these
frameworks, expect the following on first install.

**Vite (Vue / React / Solid).** `npm run preview` exists but defaults
to a randomly-allocated port unless you pass `--port`. Auto-detection
will pick `npm run preview` but `BASE_URL` defaults to
`http://localhost:3000`, which won't match. Set both explicitly in
`.icansee/env`:

```bash
SERVE_CMD="npm run preview -- --port 4173"
BASE_URL="http://localhost:4173"
```

**SvelteKit.** The `npx sv create` minimal template ships with an
`app.html` that does NOT include a `<title>` element. axe-core
correctly reports `document-title` violations on the homepage out of
the box. Add a `<title>` to `src/app.html` (or via `<svelte:head>` in
your root layout) before expecting clean runs. Same `--port` gotcha
applies for `npm run preview`.

**Angular.** `ng build` outputs to
`dist/<project-name>/browser/index.html`. Use `npx serve -s` against
that path:

```bash
SERVE_CMD="npx --yes serve -s dist/<project-name>/browser -l 4175"
BASE_URL="http://localhost:4175"
```

The Angular CLI default landing page (the "what's next" pills)
contains real `color-contrast` violations on the stock scaffold. Your
first CI run will fail. The fix is to clear out the stock landing
page, not to ignore the rule.

**Astro.** `npm run preview` defaults to port 4321. Same `--port`
flag-forwarding pattern as Vite. No template-level violations on the
minimal scaffold.

**Next.js.** Auto-detection picks `npm start` after `npm run build`.
Default port 3000 matches `BASE_URL`. No env overrides needed for the
stock scaffold.

### Browser dependency

The rendered layer uses Playwright's bundled Chromium. `install.sh` runs
`npx playwright install chromium` once during install, which downloads
the matching browser into Playwright's shared cache
(`~/.cache/ms-playwright` on Linux/macOS) and reuses it across projects.
There is no separate Chrome / Chromium / ChromeDriver install required.

If the cache is wiped or the runner reports `failed to launch chromium`,
re-run:

```bash
npx playwright install chromium
```

In CI, the workflow runs `npx playwright install --with-deps chromium`
which also installs the OS libraries the headless browser needs (fonts,
xlib, nss, etc.). That matters on minimal Linux images that don't have
those libs preinstalled.

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

The workflow's job is straightforward: install deps, install Playwright
chromium, build, start the app, hand off to `.icansee/axe-runner.mjs`
which iterates routes × color modes from `.icansee/routes.json`. The
shell logic transfers directly. Map the YAML wrapper to your provider.

### GitLab CI (`.gitlab-ci.yml`)

```yaml
a11y:
  image: mcr.microsoft.com/playwright:v1.48.0-jammy
  script:
    - npm ci
    - npm install --prefix .icansee --no-audit --no-fund
    - cd .icansee && npx playwright install chromium && cd -
    - npm run build
    - SERVE_CMD="${SERVE_CMD:-npm start}"
    - $SERVE_CMD &
    - npx --yes wait-on "${BASE_URL:-http://localhost:3000}" --timeout 60000
    - BASE_URL="${BASE_URL:-http://localhost:3000}" node .icansee/axe-runner.mjs
```

The Playwright base image has Chromium and its OS libs preinstalled.
On a plain `node:20` image, swap `playwright install chromium` for
`playwright install --with-deps chromium` instead.

### CircleCI (`.circleci/config.yml`)

```yaml
jobs:
  a11y:
    docker: [ image: mcr.microsoft.com/playwright:v1.48.0-jammy ]
    steps:
      - checkout
      - run: npm ci
      - run: npm install --prefix .icansee --no-audit --no-fund
      - run: cd .icansee && npx playwright install chromium
      - run: npm run build
      - run:
          name: Run rendered audit
          command: |
            ${SERVE_CMD:-npm start} &
            npx --yes wait-on "${BASE_URL:-http://localhost:3000}" --timeout 60000
            BASE_URL="${BASE_URL:-http://localhost:3000}" node .icansee/axe-runner.mjs
```

### Vercel (Build and Deployment Checks)

Vercel runs the toolbar's audit on preview deploys directly. The
`Accessibility Audit` permission must be granted to the project. No CI
workflow needed for the same coverage; the pre-commit gate still
applies locally.

### Bitbucket Pipelines

Same shape, in `bitbucket-pipelines.yml` with the same script body.

## Configuring routes and color modes

`.icansee/routes.json` accepts two shapes.

**Legacy array form** (still works, equivalent to light mode only):

```json
["/", "/about", "/dashboard", "/settings"]
```

**v0.3+ object form** with explicit color modes:

```json
{
  "routes": ["/", "/about", "/dashboard", "/settings"],
  "modes": ["light", "dark"]
}
```

The runner walks the cartesian product (every route × every mode) and
emulates `prefers-color-scheme` per scan. Adding `dark` doubles the
audit duration but exercises both color schemes, so a contrast bug that
only shows up against a dark background gets caught at the same gate.

If your site uses a manual `.dark` class toggle (rather than reading
`prefers-color-scheme`), the runner can't flip it for you. Either:

- Make the toggle URL-controlled (`/?theme=dark`) and add both URLs to
  `routes`, or
- Have your CSS read `prefers-color-scheme: dark` so emulation flips it.

`modes` accepts only `"light"` and `"dark"`. Anything else exits 2.

## Authenticated routes

The bundled runner does not handle login flows. Two options:

1. **Test the unauthenticated shell only**: the marketing surface,
   sign-in and sign-up pages. Often enough for the rules that are most
   commonly broken (contrast, labels, headings).
2. **Replace the runner with your own Playwright spec** that signs in
   first, then runs `@axe-core/playwright`. The bundled runner is a
   minimal starting point you can fork into `.icansee/axe-runner.mjs`.

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
