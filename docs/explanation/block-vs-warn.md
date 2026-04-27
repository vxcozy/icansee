# Why the gate blocks instead of warning

Most accessibility tooling defaults to *warning*. Findings appear in a
panel, a list, a CI step that's allowed to fail. The gate is different.
It blocks. This page explains why that's a deliberate choice and when you
should reconsider.

## The case for blocking

Warnings get ignored. A11y warnings have a long history of being shipped.
They appear next to console messages no one's reading, in CI runs no
one's looking at, in panels nobody opens. Warnings depend on attention,
and attention is scarce. Anything that depends on attention will
eventually be missed.

Blocking forces a conversation. When the gate blocks a commit, the
contributor has three choices: fix the issue, suppress it explicitly, or
push back on whether the rule applies. All three are better outcomes
than silently shipping the bug. The friction is where the decision
actually happens.

Blocking also produces cleaner histories. When fixes are required before
the commit lands, you don't get the "fix a11y" follow-up commits that
clutter the log. Every commit in `main` represents a state that passed
the gate at the time it was made.

## The case for warnings

Warnings still have a place. A few situations where they're more
appropriate than a hard block:

During exploration, when you're prototyping, blocking gates are noise.
You haven't decided yet whether this color, this layout, or this pattern
is going to stick.

For fuzzy rules, some checks need human judgment. Is this image
decorative? axe-core's `image-alt` rule treats `alt=""` as a pass
because it can't tell, but the actual decision is yours. A blocking
gate is fine for the strict cases. Warnings work better for the fuzzy
ones.

For new tooling adoption, if you turn on a strict gate against a legacy
codebase, the noise drowns the signal. Warnings let you fix
incrementally without grinding feature work to a halt.

## How icansee handles the warning case

Two ways. The escape hatch is `--no-verify`. Both `git commit
--no-verify` and `git push --no-verify` are honored. They're loud (they
show up in `git log` if you `--show-signature`, and they require an
explicit choice), and they should hurt to use.

The other option is to opt out per-layer at install time. If you want
pre-commit to warn rather than block, the answer isn't a config knob.
It's not running pre-commit. Remove the hook (`install.sh --no-hook`)
and run `scripts/audit.sh --staged` from your editor or CI for advisory
feedback instead.

## The legacy-codebase problem

If you turn on the gate against a codebase with hundreds of existing
issues, every commit breaks. That's the warning case in practice. You
need a way to fix incrementally without blocking unrelated work.

Two patterns work.

A baseline mode. Take a snapshot of current findings as the baseline,
block only on *new* findings. The skill doesn't ship this yet; it's on
the roadmap. For now, run `audit.sh --all` to take a manual baseline,
fix top-priority issues, and turn on the gate when the count is
manageable.

A severity threshold. Block on `critical` only, leave the rest as
warnings. The skill doesn't have a built-in severity flag at the hook
level either, but you can edit `audit.sh` to pass `--fail-on critical`
to `html_audit.py` and filter ESLint output similarly. This is a
customization, not a config.

For new projects, neither pattern is needed. Block everything from day
one and you'll never accumulate the legacy.

## What we deliberately rejected

A soft-block ("warn for N days, then block"). Some tools do this. We
don't, because the deadline is brittle. If N=14 and the team takes 30
days to address findings, the gate is now blocking at exactly the wrong
moment. Either you're committed to blocking or you aren't.

Per-rule severity overrides. The skill enables either an axe-core rule
or it doesn't, at the impact bucket axe-core assigns. Customizing "this
rule is critical for our project, that one is moderate" is possible by
editing the eslint configs, but it's not a first-class flow. We'd rather
inherit axe-core's calibration than ship our own.

Issue trackers and dashboards. The gate doesn't write findings to a
database, post to Slack, or open issues. It blocks a commit and prints
the findings inline. Anything more elaborate is project-specific tooling
the user can layer on top.

## When to reconsider

Block-by-default is right for most teams most of the time. Reconsider
when:

- Your codebase is so large that a baseline scan produces over 1000
  findings. Fix-as-you-go mode is gentler.
- You're a one-person prototype shop and the gate is fighting you.
  Uninstall it. Come back when you have shipping users.
- You're enforcing AAA, not AA. AAA is much stricter and many designs
  can't meet it everywhere. Use AAA as advisory and AA as blocking.

For everyone else: block. The gate exists because warnings don't work.
