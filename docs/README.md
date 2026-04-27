# icansee documentation

A three-layer WCAG 2.1 A/AA accessibility gate that blocks commits and
pushes with a11y issues. Same axe-core rule set as Vercel's Accessibility
Audit Tool.

This documentation is organized along the [Diátaxis](https://diataxis.fr)
framework. Pick the section that matches what you're trying to do right
now.

## Tutorials

For when you're new and want to learn by doing.

- [Getting started](tutorials/getting-started.md). Install in a sample
  project, watch the gate block a broken commit, fix it, watch it pass.
  About 10 minutes.

## How-to guides

For when you have a specific job to do and want a recipe.

- [How to install the icansee skill itself](how-to/install-the-icansee-skill.md)
- [How to add routes to the rendered audit](how-to/add-routes.md)
- [How to audit authenticated routes](how-to/authenticated-routes.md)
- [How to handle a slow build](how-to/slow-builds.md)
- [How to use a non-GitHub CI](how-to/non-github-ci.md)
- [How to customize build and serve commands](how-to/customize-build-and-serve.md)
- [How to audit design tokens for contrast](how-to/audit-design-tokens.md)
- [How to debug a blocked commit](how-to/debug-blocked-commit.md)
- [How to opt in or out of specific gate layers](how-to/opt-in-out-of-layers.md)
- [How to test the gate without committing](how-to/test-the-gate.md)

## Reference

For when you need to look up the exact name of a flag, env var, or rule.

- [Scripts](reference/scripts.md): every CLI flag for every script.
- [Environment variables](reference/env-vars.md): every env var the gate reads.
- [Exit codes](reference/exit-codes.md): what each script returns and why.
- [ESLint configurations](reference/eslint-configs.md): the rule set per framework.
- [Static rules](reference/static-rules.md): the axe-core WCAG A/AA rules
  the static layer enforces, and what to look for in source.
- [WCAG thresholds](reference/wcag-thresholds.md): the exact contrast
  ratios and edge cases.
- [Remediation patterns](reference/remediation-patterns.md): code-level
  fixes for the most common findings.
- [Install and CI](reference/install-and-ci.md): what `install.sh` does,
  layer comparison table, troubleshooting.

## Explanation

For when you want to understand the design rather than operate it.

- [Why three layers](explanation/three-layer-architecture.md). The gap
  between source and rendered DOM, and why we pay for three enforcement
  points.
- [Parity with Vercel's toolbar](explanation/parity-with-vercel.md).
  Where the gate matches the Vercel toolbar exactly, where it's
  approximate, and where parity doesn't hold.
- [Why we block instead of warn](explanation/block-vs-warn.md). The
  rationale for hard-blocking, and when warning would be more
  appropriate.
- [Why axe-core](explanation/why-axe-core.md). Why we inherit axe-core's
  rule set instead of inventing our own.

## Where to start

If it's your first time using the skill, start with the
[tutorial](tutorials/getting-started.md).

If you're setting up an existing project, the tutorial gives you the
right shape. Then dip into
[opt-in-out-of-layers](how-to/opt-in-out-of-layers.md) and
[add-routes](how-to/add-routes.md).

If the gate fired and you don't know why, read
[debug a blocked commit](how-to/debug-blocked-commit.md) and the
[static rules reference](reference/static-rules.md).

If you're wondering whether this fits your team, read
[why three layers](explanation/three-layer-architecture.md) and
[why block instead of warn](explanation/block-vs-warn.md).

## What this documentation isn't

It's not a WCAG primer. We assume you know what WCAG is and roughly why
it matters. The W3C's [WCAG 2.2 spec](https://www.w3.org/TR/WCAG22/) is
the authoritative reference.

It's not an axe-core API guide. axe-core is upstream; their
[docs](https://github.com/dequelabs/axe-core) cover the engine itself.

It's not an accessibility tutorial. We point you at fixes where they're
needed but don't teach screen-reader testing or assistive-tech behavior.
The [WebAIM articles](https://webaim.org/articles/) are good for that.
