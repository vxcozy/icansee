# Reference: exit codes

Consolidated table of every exit code returned by every script in the
skill.

## Convention

- `0`: clean run, no findings.
- `1`: findings detected, or operation failed in a way the caller should
  treat as a gate violation.
- `2`: input or environment error (bad args, not in a git repo, file
  missing). Distinct from `1` so callers can tell "broken setup" from
  "broken code."

## Per-script

### `install.sh`

| Code | When                                                   |
| ---- | ------------------------------------------------------ |
| 0    | Install completed.                                     |
| 2    | Not inside a git repo, or unknown command-line flag.   |

Note: `install.sh` returns 0 even if the dev-dep install fails (it
prints a warning). The hook itself will fail later with a clearer error
when ESLint isn't found.

### `audit.sh`

| Code | When                                                                      |
| ---- | ------------------------------------------------------------------------- |
| 0    | No findings, or no files in the staged/all/explicit list matched the dispatch table. |
| 1    | One or more findings.                                                     |
| 2    | Not inside a git repo.                                                    |

The hook installed by `install.sh` calls `audit.sh --staged` and
propagates this exit code, so a non-zero return blocks the commit.

### `rendered_audit.sh`

| Code | When                                                                       |
| ---- | -------------------------------------------------------------------------- |
| 0    | All routes audited successfully and found nothing.                         |
| 1    | Build failed, server didn't come up within `WAIT_TIMEOUT`, or any route had findings. |
| 2    | Not inside a git repo.                                                     |

The pre-push hook propagates this; non-zero blocks the push.

### `contrast.py`

| Code | When                                  |
| ---- | ------------------------------------- |
| 0    | Subcommand ran successfully.          |
| 2    | Argparse error (missing args, bad value). |

`contrast.py` does **not** return non-zero for a failing ratio. The
ratio is data; treat the JSON output as the source of truth.

### `palette_audit.py`

| Code | When                                       |
| ---- | ------------------------------------------ |
| 0    | Audit ran (regardless of pass/fail).       |
| 2    | Bad arguments, missing token file, or token reference to a name that doesn't exist. |

`palette_audit.py` returns 0 even when pairs fail. This is by design.
The caller (`audit.sh`) inspects the `failing_AA_normal` field in the
JSON output to decide whether to fail the gate. Treat the script as a
data producer, not a gate.

### `html_audit.py`

| Code | When                                                       |
| ---- | ---------------------------------------------------------- |
| 0    | No findings at or above the `--fail-on` level (default `any`). |
| 1    | One or more findings at or above the `--fail-on` level.    |
| 2    | I/O error opening a file.                                  |

## Hook-level interpretation

The pre-commit and pre-push hooks both:

1. Run their respective audit script.
2. Propagate the exit code to git.
3. git aborts the commit/push when the code is non-zero.

`git commit --no-verify` and `git push --no-verify` skip the hooks
entirely; they don't honor exit codes because the hooks don't run.
