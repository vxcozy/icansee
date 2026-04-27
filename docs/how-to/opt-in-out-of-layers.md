# How to opt in or out of specific gate layers

Each layer (pre-commit, pre-push, CI) catches a different class of issue.
You can install all three, none, or any combination.

## Default install

```bash
~/.claude/skills/icansee/scripts/install.sh
```

Installs all three. Most projects should keep this.

## Skip the pre-push (rendered) layer

If your build is slow enough that pre-push becomes painful, or your team
prefers waiting for CI to enforce rendered-DOM rules:

```bash
~/.claude/skills/icansee/scripts/install.sh --no-pre-push
```

You still get the pre-commit static checks locally and the rendered audit
in CI. Most teams who skip pre-push do so because their build is over a
few minutes; see [How to handle a slow build](slow-builds.md) for the full
discussion.

## Skip the CI workflow

If your CI lives somewhere other than GitHub Actions and you don't want
the YAML file in your repo:

```bash
~/.claude/skills/icansee/scripts/install.sh --no-ci
```

Translate the workflow to your provider. See
[How to use a non-GitHub CI](non-github-ci.md).

## Skip the pre-commit hook

Rare. The pre-commit layer is the cheapest layer to keep, and skipping it
loses fast author feedback. But:

```bash
~/.claude/skills/icansee/scripts/install.sh --no-hook
```

Useful if a project already has a pre-commit hook chain (lint-staged,
custom checks) and you'd rather call `audit.sh --staged` from there
manually.

## Combine flags

```bash
~/.claude/skills/icansee/scripts/install.sh --no-pre-push --no-ci
# pre-commit only

~/.claude/skills/icansee/scripts/install.sh --no-hook --no-pre-push
# CI only: gate enforced server-side, no local hooks
```

## Re-installing changes layer choice

`install.sh` is idempotent. To opt back in to a layer you skipped:

```bash
~/.claude/skills/icansee/scripts/install.sh
```

It will detect that the hook is missing (or the workflow file is missing)
and re-create it. Hand-edits to those files will be overwritten. Keep
custom rules in your own ESLint config, which icansee doesn't touch.

## Removing the gate from a project

The installer doesn't have an `--uninstall` flag because removal is
tractable in a few lines:

```bash
rm -f .git/hooks/pre-commit .git/hooks/pre-push
# or, if husky:
rm -f .husky/pre-commit .husky/pre-push

rm -rf .icansee
rm -f .github/workflows/a11y.yml
```

You can also `git revert` the install commit if you keep these in version
control.

## Verifying which layers are active

```bash
test -f .git/hooks/pre-commit && grep -q icansee .git/hooks/pre-commit \
  && echo "pre-commit: ON" || echo "pre-commit: OFF"
test -f .git/hooks/pre-push && grep -q icansee .git/hooks/pre-push \
  && echo "pre-push:   ON" || echo "pre-push:   OFF"
test -f .github/workflows/a11y.yml \
  && echo "ci:         ON" || echo "ci:         OFF"
```

Run from the repo root.
