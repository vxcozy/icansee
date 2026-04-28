# Reference: scripts

Every executable in `scripts/`, with all flags and exit codes. Authoritative
for the current revision of the skill.

---

## `install.sh`

Install the icansee gate in the current git repository.

### Usage

```
install.sh [--no-hook] [--no-pre-push] [--no-ci] [--print-detection]
install.sh -h | --help
```

### Flags

| Flag                | Effect                                                                       |
| ------------------- | ---------------------------------------------------------------------------- |
| `--no-hook`         | Skip installing the pre-commit hook.                                         |
| `--no-pre-push`     | Skip installing the pre-push hook.                                           |
| `--no-ci`           | Skip copying the GitHub Actions workflow.                                    |
| `--print-detection` | Detect frameworks, print the result, exit. Does not modify anything.         |
| `-h`, `--help`      | Print usage from the script header and exit.                                 |

### Side effects

- Creates `.icansee/` in the repo root.
- Copies one or more `.icansee/eslint-*.config.mjs` files based on detection.
- Installs ESLint plugin packages as devDependencies via the project's
  package manager (npm/pnpm/yarn/bun).
- Writes the pre-commit hook to `.husky/pre-commit` (if husky is present)
  or `$(git rev-parse --git-path hooks)/pre-commit`.
- Same for pre-push.
- Copies `.github/workflows/a11y.yml`.
- Creates `.icansee/routes.json` if not already present.

### Exit codes

| Code | Meaning                                       |
| ---- | --------------------------------------------- |
| 0    | Install completed (warnings are non-fatal).   |
| 2    | Not inside a git repo, or unknown flag.       |

---

## `audit.sh`

Run the static (pre-commit) layer.

### Usage

```
audit.sh [--staged | --all | FILE...]
audit.sh -h | --help
```

### Modes

| Mode      | Behavior                                                                  |
| --------- | ------------------------------------------------------------------------- |
| `--staged`| Default. Audits files in `git diff --cached --name-only --diff-filter=ACMR`. |
| `--all`   | Audits every tracked file in the repo.                                    |
| `FILE...` | Audits the listed paths only. Files don't need to be tracked.             |

### File buckets and dispatch

| Extension(s)         | Tool                                                                |
| -------------------- | ------------------------------------------------------------------- |
| `.jsx`, `.tsx`       | `npx eslint --config .icansee/eslint-jsx-a11y.config.mjs`           |
| `.vue`               | `npx eslint --config .icansee/eslint-vuejs-a11y.config.mjs`         |
| `.svelte`            | `npx eslint --config .icansee/eslint-svelte-a11y.config.mjs`        |
| `.component.html`, `.html` (in Angular projects) | `npx eslint --config .icansee/eslint-angular-template-a11y.config.mjs` |
| `.astro`             | `npx eslint --config .icansee/eslint-astro-a11y.config.mjs`         |
| `.html`, `.htm`      | `python3 scripts/html_audit.py`                                     |
| `.icansee/palette.json` (when present) | `python3 scripts/palette_audit.py matrix`                |

Angular detection: a file at `<repo>/angular.json` switches `.html`
files into the Angular template bucket.

### Exit codes

| Code | Meaning                                                |
| ---- | ------------------------------------------------------ |
| 0    | No findings, or no files matched the dispatch table.   |
| 1    | One or more findings. Pre-commit hook will block.      |
| 2    | Not inside a git repo.                                 |

---

## `rendered_audit.sh`

Run the rendered (pre-push / CI) layer.

### Usage

```
rendered_audit.sh
```

No flags. Configuration via env vars or `.icansee/env`.

### Env vars

| Var            | Default                                                | Purpose                                         |
| -------------- | ------------------------------------------------------ | ----------------------------------------------- |
| `BUILD_CMD`    | `npm run build` if `package.json` has a build script   | Command to build the project.                   |
| `SERVE_CMD`    | First match of `npm start`, `npm run preview`, `npx --yes serve -s . -p 3000` | Command to start the app.                       |
| `BASE_URL`     | `http://localhost:3000`                                | Where the served app listens.                   |
| `WAIT_TIMEOUT` | `60000`                                                | Milliseconds to wait for server readiness.      |

`.icansee/env` is sourced before defaults are applied. Shell variables in
the parent environment override `.icansee/env`.

### Side effects

- Runs `BUILD_CMD` if non-empty.
- Starts `SERVE_CMD` in the background.
- Waits via `npx --yes wait-on "$BASE_URL"` up to `WAIT_TIMEOUT` ms.
- Hands off to `node .icansee/axe-runner.mjs` (Playwright +
  `@axe-core/playwright`), which iterates every `route × color-mode`
  combination from `.icansee/routes.json` with the WCAG tag set
  `wcag2a,wcag2aa,wcag21a,wcag21aa`. Defaults to `["/"]` and
  `["light"]` when the file is missing.
- Logs server output to `/tmp/icansee-serve.log`.
- Kills the server on exit (any code path, via trap).

### Exit codes

| Code | Meaning                                                       |
| ---- | ------------------------------------------------------------- |
| 0    | Audit clean across all routes and modes.                      |
| 1    | Build failed, server didn't come up, or any route × mode had findings. |
| 2    | Not inside a git repo, missing `.icansee/axe-runner.mjs`, or runner infra error (e.g. chromium missing). |

---

## `contrast.py`

Compute WCAG contrast ratios.

### Usage

```
contrast.py check FOREGROUND BACKGROUND [--human]
contrast.py suggest FOREGROUND BACKGROUND [--target N] [--direction auto|darker|lighter]
contrast.py pair FOREGROUND BACKGROUND
```

### Subcommands

#### `check`

Compute the ratio and pass/fail at AA normal, AA large, AAA normal, AAA
large, and 1.4.11 non-text.

| Flag       | Effect                                                     |
| ---------- | ---------------------------------------------------------- |
| `--human`  | One-line human-readable output instead of JSON.            |

#### `suggest`

Find a hue-preserving foreground that meets the target ratio.

| Flag                    | Default | Effect                                                                   |
| ----------------------- | ------- | ------------------------------------------------------------------------ |
| `--target N`            | 4.5     | Required ratio.                                                          |
| `--direction MODE`      | auto    | `darker`, `lighter`, or `auto` (picks based on background luminance).    |

#### `pair`

Alias for `check --human`.

### Color formats accepted

- `#rgb`, `#rrggbb`, `#rgba`, `#rrggbbaa`
- `rgb(r, g, b)`, `rgba(r, g, b, a)`

Translucent foregrounds are composited against the background before the
ratio is measured.

### Exit codes

| Code | Meaning                              |
| ---- | ------------------------------------ |
| 0    | Computation succeeded.               |
| 2    | Argparse error (missing args, etc.). |

The script does **not** exit non-zero on a failing ratio. Failure/pass is
data, not an error condition. Inspect the JSON `passes` map.

---

## `palette_audit.py`

Audit a palette of design tokens for AA contrast compliance.

### Usage

```
palette_audit.py matrix TOKENS [--foregrounds A,B,C] [--backgrounds X,Y]
palette_audit.py pairs  TOKENS --pair fg:bg [--pair fg:bg ...]
```

### Token formats accepted

- JSON: `{ "name": "#hex", ... }` or `{ "name": { "value": "#hex" } }`
- CSS: top-level `--name: #hex;` custom properties

### `matrix` flags

| Flag                | Default                         | Effect                                                         |
| ------------------- | ------------------------------- | -------------------------------------------------------------- |
| `--foregrounds A,B` | All tokens                      | Comma-separated names to use as foregrounds.                   |
| `--backgrounds X,Y` | All tokens                      | Comma-separated names to use as backgrounds.                   |

### `pairs` flags

| Flag             | Required | Effect                                              |
| ---------------- | -------- | --------------------------------------------------- |
| `--pair fg:bg`   | yes      | A single fg/bg pair. Can be repeated.               |

### Output

JSON. Each result has the same fields as `contrast.py check` plus
`fg_hex` / `bg_hex`, plus `suggested_fg` / `suggested_ratio` for failing
pairs.

### Exit codes

| Code | Meaning                                  |
| ---- | ---------------------------------------- |
| 0    | Audit completed.                         |
| 2    | Bad arguments or token files not found.  |

---

## `html_audit.py`

Static HTML accessibility check.

### Usage

```
html_audit.py [FILE ...] [--human] [--fail-on LEVEL]
```

If no files are passed, reads from stdin.

### Flags

| Flag                        | Default | Effect                                                                          |
| --------------------------- | ------- | ------------------------------------------------------------------------------- |
| `--human`                   | off     | Human-readable output. Default is JSON.                                         |
| `--fail-on LEVEL`           | `any`   | Exit non-zero when findings reach this impact. One of `any`, `minor`, `moderate`, `serious`, `critical`. |

### Rules covered

See [static-rules.md](static-rules.md) for the full list with axe-core
parity notes.

### Exit codes

| Code | Meaning                                                   |
| ---- | --------------------------------------------------------- |
| 0    | No findings at or above the fail-on level.                |
| 1    | One or more findings at or above the fail-on level.       |
| 2    | I/O error reading a file.                                 |
