# Why three layers

The icansee gate has three enforcement points: a pre-commit hook, a
pre-push hook, and a CI workflow. That's one more than most a11y tools
use. Here's why.

## The honest gap

Static analysis can read source code. It cannot read CSS as it cascades
through the DOM, observe focus states, or measure landmark coverage of a
rendered tree. There's a class of WCAG failures that simply cannot be
detected from source alone:

- Computed contrast through inheritance. `<p class="warning">` tells you
  nothing about contrast on its own. The actual ratio depends on every
  CSS rule that touches `.warning`, `p`, and the body's `color` and
  `background-color`.
- Focus-state contrast. The default browser focus ring has poor contrast
  on many backgrounds, but you can't see that from source if the styles
  override `outline`.
- Landmark coverage. Whether `<main>` actually contains the bulk of the
  page's content is a function of the rendered tree, not the source.

Tools like Vercel's Accessibility Audit, axe-core in DevTools, and Chrome's
Lighthouse all run against the rendered DOM for this reason. Source-only
linters miss this entire class.

A two-layer gate (pre-commit + CI) handles this honestly. Pre-commit is
fast and static, CI runs against the rendered DOM and is the parity layer.
That's a sensible default for many projects.

But there's still a problem.

## Why CI alone isn't enough as a block

A two-layer gate (pre-commit + CI) leaves a window between local commit
and PR creation. During that window, contributors may:

1. Push a branch that has rendered-DOM violations.
2. Open a PR.
3. Wait for CI to finish (5+ minutes).
4. See the failure, fix it, push again.

This works, but it has costs.

The biggest is feedback latency. A 5-minute round-trip for findings that
could be caught locally in 30 to 90 seconds adds up across a working day.
PR history also gets noisy: "fix a11y" follow-up commits pile up after
the initial push when the same change could have shipped clean. And it
makes the gate dependent on CI uptime. GH Actions queues, runners die,
builds flake. Local enforcement doesn't.

A third layer at pre-push closes that window. The contributor sees
findings before the code leaves the machine, fixes them in the same
session, and only one clean commit gets pushed.

## Why not run the heavy check at pre-commit instead?

The obvious alternative is to drop pre-push and run the rendered audit at
every commit. We rejected this for two reasons.

First, commits should be fast. Sub-second feedback feels like part of the
editor; multi-second feedback breaks flow. People stop committing as
often when each commit takes ten seconds, which is bad for both code
quality and bisecting later.

Second, most commits don't change the rendered output. Documentation
edits, refactors, internal refactors of pure functions, none of these
need a rendered-DOM audit. Running it on every commit means paying the
cost on commits that couldn't possibly fail it.

Pre-push is the right granularity. The audit runs once per push, not per
commit, so the wall-clock cost is amortized across however many commits
you're pushing.

## Why CI when pre-push exists

`git push --no-verify` exists. People will use it, sometimes for good
reasons (a hotfix, a known-broken WIP branch), sometimes from
frustration.

CI is the layer that contributors can't bypass on their own. The PR
cannot merge until it's clean. This is non-negotiable for the
"block before it ships" property. Without CI, the gate is advisory, not
mandatory.

## The shape we settled on

| Layer       | Job                                              | Bypass            |
| ----------- | ------------------------------------------------ | ----------------- |
| Pre-commit  | Catch source-level issues fast.                  | `--no-verify`     |
| Pre-push    | Close the rendered-DOM gap before code leaves.   | `--no-verify`     |
| CI          | Final ungame-able check at the merge boundary.   | None, by design.  |

Each layer adds a class of issue that the layer below it can't catch, or
adds a property the layer below it doesn't have. Removing any one of them
loses something:

- Without pre-commit: slow feedback on the cheap-to-catch issues.
- Without pre-push: 5-minute round-trip for the rendered-DOM issues.
- Without CI: no enforcement when contributors bypass.

## What we accepted by choosing this shape

There are three places to maintain config now. Routes for the rendered
audit are shared between pre-push and CI (same `.icansee/routes.json`),
and the ESLint configs are shared between pre-commit and (eventually)
editor lint. The layers can drift if you're not careful.

Pre-push hurts when builds are slow. A 3-minute build is a 3-minute wait
on every push. Mitigations exist (see
[How to handle a slow build](../how-to/slow-builds.md)) but at some point
you opt out of pre-push and rely on CI.

There's no Storybook-style component-isolation testing either. The
rendered audit hits real routes, not isolated components, which means it
doesn't catch things like "this Modal is only ever rendered in error
states." That's a real gap. Closing it would mean adding a fourth layer
or pulling Storybook into scope. We chose not to.

## Alternative shapes we considered

**JSDOM at pre-commit.** Render JSX/Vue/Svelte components in JSDOM, run
axe-core against the result, get fast rendered-DOM checks at commit time.
Rejected because JSDOM doesn't fully match a real browser. There's no
actual layout, focus-state tracking is weaker, and CSS-in-JS often doesn't
apply. So the result would be neither fast (component rendering needs
context and props that real components require) nor authoritative.

**Pre-push and skip CI.** Lighter ops surface, faster local feedback.
Rejected because `--no-verify` turns it back into something advisory.

**CI only.** Simplest. Rejected because the local feedback loop matters
for adoption. If every a11y issue means a 5-minute CI round-trip, people
stop trying.

The three-layer shape is what gives fast author feedback, closes the
rendered-DOM gap before push, and provides an ungame-able boundary at
the PR. Drop any of the three and you lose one of those.
