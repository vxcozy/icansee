# How to install the icansee skill itself

Three ways to make the icansee skill available to Claude on your machine,
depending on whether you're a user, a contributor, or just trying it out.

The skill needs to live at one of the directories Claude Code searches for
skills:

- `~/.claude/skills/<name>/`: user-scoped, available everywhere.
- `<project>/.claude/skills/<name>/`: project-scoped, only available
  inside that project.

The directory name (`<name>`) matters: it must match the `name` field in
`SKILL.md`'s frontmatter. For icansee, that's `icansee`.

## Option 1: symlink from a development checkout (recommended for contributors)

If you're editing the skill or following along with a working tree (e.g.,
under `~/Projects/iCanSee/icansee/`), symlink it into the skills directory.
That way edits are immediately picked up by Claude.

```bash
mkdir -p ~/.claude/skills
ln -s ~/Projects/iCanSee/icansee ~/.claude/skills/icansee
```

Verify:

```bash
ls -l ~/.claude/skills/icansee
# icansee -> /Users/you/Projects/iCanSee/icansee
ls ~/.claude/skills/icansee/SKILL.md
```

That's it. Open Claude Code, the skill is loadable.

If you put your checkout somewhere else, point the symlink at that path:

```bash
ln -s /absolute/path/to/icansee ~/.claude/skills/icansee
```

To remove it later:

```bash
rm ~/.claude/skills/icansee
```

`rm` on a symlink only removes the link; the original directory is not
touched.

### Project-scoped symlink

If you want the skill available only inside one project (e.g., a team that
shares a Claude config in-repo):

```bash
mkdir -p .claude/skills
ln -s /absolute/path/to/icansee .claude/skills/icansee
git add .claude/skills/icansee  # if you want to commit the symlink
```

Note: committed symlinks resolve on the machine they're checked out on. If
your team uses different absolute paths, prefer copying or vendoring the
skill into the repo instead of symlinking.

## Option 2: clone fresh into the skills directory

If you don't have a working tree and just want to use the skill, clone (or
copy) it directly:

```bash
mkdir -p ~/.claude/skills
git clone <repo-url> ~/.claude/skills/icansee
```

Or, if you have a tarball / zip:

```bash
mkdir -p ~/.claude/skills
tar -xzf icansee.tar.gz -C ~/.claude/skills/
mv ~/.claude/skills/icansee-* ~/.claude/skills/icansee  # rename if needed
```

Updates require pulling or re-extracting. Use Option 1 if you're iterating.

## Option 3: install via skills.sh

If the skill is published to skills.sh and you have its CLI installed:

```bash
skills install icansee
```

The skills.sh CLI handles the directory placement for you. See
https://skills.sh for details.

## Verify the install

After any of the above:

```bash
test -f ~/.claude/skills/icansee/SKILL.md && echo "OK" || echo "MISSING"
```

Expected: `OK`.

You can also ask Claude directly: "what skills do you have access to?"
It should list `icansee` along with a one-line description.

## Test that it works

Run the bundled scripts directly to confirm the skill is wired up:

```bash
~/.claude/skills/icansee/scripts/contrast.py check "#777" "#fff" --human
```

Expected output:

```
#777 on #fff: 4.48:1 ... AA normal FAIL, AA large PASS, ...
```

If you get `command not found`, check that the path resolves and that
`scripts/contrast.py` is executable (`ls -l`). If the file isn't
executable, `chmod +x ~/.claude/skills/icansee/scripts/*.py
~/.claude/skills/icansee/scripts/*.sh` fixes it.

## Updating

- **Symlink**: pull / edit in the source tree. No re-link needed.
- **Clone**: `git -C ~/.claude/skills/icansee pull`.
- **skills.sh**: `skills upgrade icansee` (check the CLI for exact syntax).

## Uninstalling

```bash
rm ~/.claude/skills/icansee   # symlink: removes link only
# or
rm -rf ~/.claude/skills/icansee  # clone: removes the entire copy
```

If you previously ran `scripts/install.sh` inside a project, that left
hooks in `.git/hooks/pre-commit` and `.git/hooks/pre-push` (or `.husky/`)
plus a `.icansee/` directory and `.github/workflows/a11y.yml`. To remove
those:

```bash
cd <project>
rm -f .git/hooks/pre-commit .git/hooks/pre-push
rm -rf .icansee .github/workflows/a11y.yml
```

Or, if you're using husky:

```bash
rm -f .husky/pre-commit .husky/pre-push
```

## Troubleshooting

**Claude doesn't see the skill.** Make sure the directory is exactly
`~/.claude/skills/icansee/` and that `SKILL.md` exists at its root with the
`name: icansee` frontmatter. Restart Claude Code.

**Symlink resolves but scripts fail.** macOS sometimes denies execution of
files in synced directories (iCloud, Dropbox). Move the source tree out of
the sync path.

**Permission denied on scripts.** Re-run:

```bash
chmod +x ~/.claude/skills/icansee/scripts/*
```
