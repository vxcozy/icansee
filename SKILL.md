---
name: icansee
description: Install and operate a three-layer WCAG 2.1 A/AA accessibility gate that blocks commits and pushes with a11y issues. Same axe-core rule set as Vercel's Accessibility Audit Tool. Layers are (1) a pre-commit hook running static checks (jsx-a11y, vuejs-accessibility, svelte, angular-template, astro, plain HTML, palette tokens) on staged files, (2) a pre-push hook running Playwright + @axe-core/playwright against the built and served site to catch rendered-DOM rules (computed contrast, landmark coverage, focus state) and to sweep light/dark color modes via prefers-color-scheme emulation, and (3) a GitHub Actions workflow enforcing the same rendered audit at the PR boundary. Also handles on-demand reviews like contrast ratio checks, palette audits, and snippet reviews. Use when the user asks to set up a11y CI, block accessibility issues at commit, audit a palette, check a contrast ratio, or review code for WCAG compliance.
---

# icansee: accessibility gate and reviewer

This skill installs and operates a three-layer WCAG 2.1 A/AA gate that
blocks accessibility regressions before they ship. Same rule set as the
Vercel toolbar's Accessibility Audit Tool (axe-core).

It also serves as an on-demand reviewer for contrast questions, palette
audits, and snippet reviews when the user isn't asking for a full
install.

## When to use

- "set up / install a11y / accessibility checks in this repo"
- "block commits with accessibility issues"
- "configure WCAG / axe-core compliance"
- "review this for a11y / WCAG"
- "does color X on Y pass AA / AAA"
- "audit my design tokens / palette"
- The user is in a project that already has `.icansee/`. The skill is
  active there. Keep edits consistent with its conventions.

## Architecture (so you can answer questions about it)

Three layers, complementary:

| Layer        | Trigger        | Engine                                                              | Catches                                                                                  | Speed     |
| ------------ | -------------- | ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | --------- |
| Pre-commit   | `git commit`   | `audit.sh` → eslint plugins + `html_audit.py` + `palette_audit.py`  | Source-level rule violations on staged files: missing alt, no label, bad ARIA, palette failures. | ~1–3s    |
| Pre-push     | `git push`     | `rendered_audit.sh` → Playwright + `@axe-core/playwright` against built+served site, sweeping configured color modes | Rendered-DOM rules that source can't see: computed contrast through CSS cascade, landmark coverage, focus state, dark-mode contrast via `prefers-color-scheme` emulation. | ~30–90s  |
| CI           | PR / push      | Same as pre-push, in GitHub Actions (`.github/workflows/a11y.yml`)  | Same as pre-push, but enforced at the merge boundary where `--no-verify` cannot help.    | ~1–5min  |

Why three layers, not two:

- The pre-commit gate is fast enough to run on every commit. It's
  static-only by design, which keeps each-commit feedback under a few
  seconds.
- The pre-push gate closes the rendered-DOM gap locally. Same engine as
  the Vercel toolbar's Accessibility Audit Tool. It runs once per push,
  not per commit, so wall-clock cost is amortized.
- CI is the ungame-able boundary. `git push --no-verify` skips pre-push;
  CI doesn't honor it. Required because contributors *will* `--no-verify`
  at some point.

All three block on any issue. Bypasses are deliberate escape hatches:
`git commit --no-verify` for pre-commit, `git push --no-verify` for
pre-push, no bypass for CI.

## Capability table

| Need                                          | How                                                                  |
| --------------------------------------------- | -------------------------------------------------------------------- |
| Install the gate in a repo                    | Run `scripts/install.sh` from the repo root.                         |
| Detect what frameworks are present            | `scripts/install.sh --print-detection`                               |
| Lint staged files manually                    | `scripts/audit.sh --staged`                                          |
| Lint everything in the repo                   | `scripts/audit.sh --all`                                             |
| Lint specific files                           | `scripts/audit.sh path/to/file.tsx`                                  |
| Run rendered-DOM audit locally                | `scripts/rendered_audit.sh` (builds, serves, runs Playwright + axe per route × mode) |
| Check one contrast pair                       | `scripts/contrast.py check <fg> <bg>`                                |
| Suggest a passing color                       | `scripts/contrast.py suggest <fg> <bg> --target 4.5`                 |
| Audit a palette / token file                  | `scripts/palette_audit.py matrix tokens.json`                        |
| Static HTML a11y check                        | `scripts/html_audit.py page.html`                                    |
| Threshold lookup                              | `docs/reference/wcag-thresholds.md`                                  |
| Per-rule check guidance                       | `docs/reference/static-rules.md`                                     |
| Code-level fixes                              | `docs/reference/remediation-patterns.md`                             |
| Install flow / CI translation / troubleshooting | `docs/reference/install-and-ci.md`                                 |

## Workflow: three common shapes

### A. Install or configure the gate

When the user asks to set this up in their project:

1. Confirm the cwd is a git repo. If not, offer to run `git init` first.
2. Run `scripts/install.sh` and surface its output. The installer
   detects frameworks from package.json and filesystem hints, installs
   the right ESLint plugin(s) via the project's package manager
   (npm/pnpm/yarn/bun, picked from lockfile), drops flat-config files
   into `.icansee/`, wires the pre-commit hook into `.husky/` (if husky
   is present) or `.git/hooks/pre-commit`, and copies
   `.github/workflows/a11y.yml` along with `.icansee/routes.json`.
3. Walk the user through `.icansee/routes.json`. List the routes that
   exercise the UI surface that matters. Default is `["/"]` (light mode
   only). To sweep dark mode too, use the v0.3 object form:
   `{"routes": ["/"], "modes": ["light", "dark"]}`.
4. Suggest a smoke test: stage an intentional violation and try to
   commit.
5. If the user is **not** on GitHub Actions, point them at
   `docs/reference/install-and-ci.md` for translations to GitLab,
   CircleCI, Bitbucket, or Vercel.

### B. The gate fired on a commit and the user asks for help

The pre-commit output prints `file:line:col [impact] rule: message` per
finding. For each:

1. Identify the rule by matching against
   `docs/reference/static-rules.md`.
2. Read the offending file at the indicated line.
3. Apply the canonical fix from
   `docs/reference/remediation-patterns.md` or tailor to the user's
   stack.
4. Re-stage and re-run `scripts/audit.sh --staged` to verify before
   suggesting they commit.
5. **Never recommend `git commit --no-verify` as a fix.** It's an escape
   hatch only, and only if the user explicitly chooses it.

### C. Ad-hoc review (no install requested)

Use the on-demand scripts directly. Three sub-shapes:

- "Does color X on Y pass?" Call `scripts/contrast.py check`. Report
  the exact ratio plus pass/fail at AA normal, AA large, AAA normal, AAA
  large, and 1.4.11 non-text. If failing, run `scripts/contrast.py
  suggest`.
- "Audit this palette / token file." Run `scripts/palette_audit.py
  matrix`. Group by failing pair count; surface suggested replacements
  for each.
- "Review this component / page." Read source. Walk the categories in
  `docs/reference/static-rules.md`. For every text element with
  resolvable foreground/background, run `scripts/contrast.py`. Group
  findings by severity. Anything needing a rendered DOM goes in the
  "manual review" bucket. Recommend the CI path or running the Vercel
  toolbar locally.

## Reporting findings

Lead with the count, like `3 must-fix, 2 should-fix, 1 needs manual
review`. Each finding includes:

- Where: `file_path:line_number`.
- Rule: axe-core rule id and WCAG SC (e.g., `color-contrast`, 1.4.3 AA).
- What's wrong: one sentence.
- Fix: concrete code or color change. Pull from
  `docs/reference/remediation-patterns.md` when it fits.
- For contrast: ratio achieved, threshold, suggested color.

## Constraints

- Use the scripts; don't estimate. Contrast is exact math. Reported
  ratios must match what axe-core, DevTools, and WebAIM produce.
- Never round near a threshold. 4.49:1 fails AA. Say so.
- Disabled controls (`disabled` attr or `aria-disabled="true"` with
  enforced behavior) are exempt from 1.4.3 and 1.4.6.
- Don't recommend ARIA where native HTML works. A `<button>` already has
  `role="button"`; adding it is noise.
- Don't auto-fix without asking. Report findings, propose fixes, let the
  user pick which to apply.
- Pre-commit alone is not parity with Vercel's toolbar. It's static.
  The pre-push and CI layers are the parity layers (same axe-core
  engine). Be honest about this when the user asks what each layer
  catches.

## Pointers

- `scripts/install.sh`: project installer, idempotent. Default installs
  all three layers; `--no-pre-push`, `--no-ci`, `--no-hook` opt out
  individually.
- `scripts/audit.sh`: pre-commit entrypoint and CLI runner.
- `scripts/rendered_audit.sh`: pre-push entrypoint. Build, serve, hand
  off to `.icansee/axe-runner.mjs` (Playwright + `@axe-core/playwright`).
  Honors `BUILD_CMD`, `SERVE_CMD`, `BASE_URL` env or `.icansee/env` file.
- `templates/axe-runner.mjs`: the per-route × per-mode axe runner. Copied
  to `.icansee/axe-runner.mjs` at install time.
- `scripts/contrast.py`: exact WCAG ratio plus suggest.
- `scripts/palette_audit.py`: token matrix audit.
- `scripts/html_audit.py`: stdlib static HTML a11y check.
- `templates/eslint/*.config.mjs`: flat-config rule sets per framework.
- `templates/pre-commit`: git pre-commit hook script.
- `templates/pre-push`: git pre-push hook script (skips when only docs
  change).
- `templates/github-workflow-a11y.yml`: CI workflow that runs the same
  Playwright + axe runner.
- `docs/`: full human-readable documentation, organized via the
  [Diátaxis](https://diataxis.fr) framework. Start at
  [docs/README.md](docs/README.md). Sections:
  - `docs/tutorials/`: guided walkthroughs (start with
    `getting-started.md`).
  - `docs/how-to/`: task recipes (install, routes, auth, slow builds,
    non-GitHub CI, debug a blocked commit, opt-in/out of layers).
  - `docs/reference/`: authoritative lookups (scripts, env vars, exit
    codes, ESLint configs, WCAG thresholds, static rules, remediation
    patterns, install-and-ci).
  - `docs/explanation/`: design rationale (three-layer architecture,
    parity with Vercel, block vs warn, why axe-core).
- Spec: https://www.w3.org/TR/WCAG22/
- axe-core rules: https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md
- Vercel parity: https://vercel.com/docs/vercel-toolbar/accessibility-audit-tool
