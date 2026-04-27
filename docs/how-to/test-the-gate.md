# How to test the gate without committing

Sometimes you want to see what the gate would say without going through
`git commit`. Three ways.

## Run the static layer on your staged files

```bash
git add path/to/file.tsx
~/.claude/skills/icansee/scripts/audit.sh --staged
```

Same checks the pre-commit hook runs, no commit happens. Useful when
iterating on a fix.

## Run the static layer on every tracked file

```bash
~/.claude/skills/icansee/scripts/audit.sh --all
```

Audits the whole repo, not just staged changes. Slow on large repos but
gives you the complete current state. Useful when you've just installed
the gate and want a baseline.

## Run on specific files

```bash
~/.claude/skills/icansee/scripts/audit.sh src/components/SignUp.tsx \
                                          public/landing.html
```

Overrides the staged-files default. Files don't need to be tracked by git.

## Run only the rendered layer

```bash
~/.claude/skills/icansee/scripts/rendered_audit.sh
```

Builds, serves, runs `@axe-core/cli`. Same as the pre-push hook. Useful if
you want to verify a rendered fix without pushing.

## Run only the contrast script

```bash
~/.claude/skills/icansee/scripts/contrast.py check "#2563eb" "#ffffff" --human
```

For one-off questions about whether a color pair passes.

## Run only the palette audit

```bash
python3 ~/.claude/skills/icansee/scripts/palette_audit.py matrix tokens.json
```

For checking a token file outside the pre-commit flow.

## Run only the HTML audit

```bash
python3 ~/.claude/skills/icansee/scripts/html_audit.py public/index.html --human
```

For checking a single HTML file directly. The pre-commit hook calls this
internally for `.html` files.

## Smoke-test that the gate actually fires

Create a deliberately broken file, stage it, attempt a commit:

```bash
echo '<img src="x.png">' > /tmp/test.html
git add /tmp/test.html  # only works if /tmp is tracked; usually it isn't
```

Or in the repo:

```bash
echo '<img src="x.png">' > test-icansee.html
git add test-icansee.html
git commit -m "test"   # should fail
git reset HEAD test-icansee.html
rm test-icansee.html
```

You should see `image-alt: <img> missing alt`. If you don't, the hook
isn't installed. See
[How to debug a blocked commit](debug-blocked-commit.md) → "When the gate
doesn't load at all."
