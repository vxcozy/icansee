# Getting started with icansee

About 10 minutes. By the end you'll have:

- The pre-commit gate installed in a small project.
- Watched it block a commit because the page is missing an alt attribute.
- Fixed the issue and watched it accept the next commit.
- Seen what runs in the rendered (pre-push) layer and how to fire it
  manually.

You don't need a real frontend project. We'll build the smallest possible
one from scratch.

## What you'll need

- A Mac or Linux shell with `bash`, `git`, and `python3` (3.8+).
- About 50 MB of disk space.
- Optional: `node` and `npx`, if you want to run the rendered (pre-push)
  layer at the end. The pre-commit layer works without Node.

You don't need to install anything globally. The skill ships everything
it needs.

## 1. Create a sandbox project

Open a terminal and run:

```bash
mkdir hello-icansee
cd hello-icansee
git init
git config user.email "you@example.com"  # any value is fine
git config user.name "You"
```

Now drop in an HTML file with a few real problems in it. Don't fix them.
We want the gate to find them in a moment.

```html
<!-- index.html -->
<!doctype html>
<html>
<body>
  <img src="/logo.png">
  <button></button>
  <input type="email" placeholder="Email">
</body>
</html>
```

There are four issues hiding in those eight lines. Let the gate point
them out for you.

## 2. Install the gate

The path below assumes the icansee skill lives at
`~/.claude/skills/icansee/`. If you haven't set that up yet, see
[How to install the icansee skill itself](../how-to/install-the-icansee-skill.md).
A one-line `ln -s` is usually enough. Adjust the paths below if you put
it somewhere else.

```bash
~/.claude/skills/icansee/scripts/install.sh
```

The installer prints what it does. You'll see something like:

```
icansee: detected frameworks: html-only
icansee: pre-commit hook installed at .git/hooks/pre-commit
icansee: pre-push hook installed at .git/hooks/pre-push
icansee: CI workflow installed at .github/workflows/a11y.yml
```

Three things just happened. A pre-commit hook was wired into your local
repo. A pre-push hook was wired in too. And a GitHub Actions workflow was
dropped at `.github/workflows/a11y.yml` for when you eventually push to
GitHub.

For this tutorial we only care about the pre-commit hook.

## 3. Try to commit the broken page

```bash
git add index.html
git commit -m "first page"
```

The commit will not go through. Instead you'll see something like this:

```
▸ Plain HTML (icansee/html_audit.py)
index.html:2:0 [serious]   html-has-lang: <html> missing lang attribute
index.html:4:2 [critical]  image-alt:    <img> missing alt; use alt="" for decorative images
index.html:5:2 [critical]  button-name:  <button> has no accessible name
index.html:6:2 [critical]  label:        <input> has no associated label
index.html:3:0 [serious]   document-title: document is missing a non-empty <title>

5 finding(s)

icansee: ✗ a11y findings detected, commit blocked.
        Fix the issues above. To bypass (not recommended), use:
        git commit --no-verify
```

Each line tells you the file, line, column, severity, the axe-core rule
that fired, and a one-line explanation. The commit was rolled back;
nothing landed in your history.

## 4. Fix the issues

Replace `index.html` with a clean version:

```html
<!doctype html>
<html lang="en">
<head>
  <title>Hello icansee</title>
</head>
<body>
  <img src="/logo.png" alt="">
  <button aria-label="Close">×</button>
  <label for="email">Email</label>
  <input id="email" type="email">
</body>
</html>
```

What changed and why:

- `lang="en"` on `<html>`. The document needs a language so screen
  readers pronounce it correctly.
- A non-empty `<title>`. Every document needs one.
- `alt=""` on the image. This is the correct value for a decorative
  image. A missing `alt` attribute is a fail; an empty `alt` is a
  deliberate "this is decoration."
- `aria-label="Close"` and visible text on the button. Buttons need an
  accessible name.
- A real `<label for="email">` linked to the input. `placeholder` is not
  a label.

## 5. Commit again

```bash
git add index.html
git commit -m "first page"
```

This time:

```
▸ Plain HTML (icansee/html_audit.py)
ok: no static a11y findings

icansee: ✓ no a11y findings on 1 file(s)
[main (root-commit) ...] first page
 1 file changed, 10 insertions(+)
```

The pre-commit gate ran in under a second, found nothing wrong, and let
the commit through.

## 6. (Optional) Watch the rendered layer

If you have Node installed, you can manually run the pre-push layer too.
It builds the project (skipped here since there's nothing to build),
starts a local server, and runs `@axe-core/cli` against the routes in
`.icansee/routes.json`.

```bash
~/.claude/skills/icansee/scripts/rendered_audit.sh
```

Behind the scenes:

1. Detects there's no `npm run build` script and skips the build step.
2. Falls back to `npx serve -s . -p 3000` to serve the static files.
3. Waits for `http://localhost:3000` to come up.
4. Runs `npx @axe-core/cli http://localhost:3000/` with the WCAG A/AA
   tags.
5. Kills the server.

Because the page is clean, the rendered audit also passes. If we'd left
a `color: #999` on a white background somewhere, the static layer
wouldn't catch it (the source HTML is fine), but the rendered layer
would.

That's the gap the third layer closes.

## 7. What just happened, in summary

You installed a three-layer gate that enforces WCAG 2.1 A/AA at
progressively heavier checkpoints. Pre-commit ran in about a second on
every `git commit`. It looked at the source and found 5 things wrong with
the first version. Pre-push would run on every `git push`. It builds,
serves, and runs axe-core against the rendered DOM, the same engine
Vercel's toolbar uses. CI runs the same rendered audit on GitHub
Actions. It can't be bypassed with `--no-verify`, so even if someone
slipped a broken commit past their local hooks, the PR can't merge until
it's clean.

## Where to go next

- Add real routes to scan: edit `.icansee/routes.json`. See
  [How to add routes to the rendered audit](../how-to/add-routes.md).
- Translate the GitHub workflow to your CI: see
  [How to use a non-GitHub CI](../how-to/non-github-ci.md).
- Understand why three layers, not two: see
  [Why three layers](../explanation/three-layer-architecture.md).
- Look up a specific script flag: see
  [Reference: scripts](../reference/scripts.md).

## Cleanup

If you want to throw away the sandbox:

```bash
cd ..
rm -rf hello-icansee
```

The icansee skill itself stays put.
