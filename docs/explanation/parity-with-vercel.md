# Parity with Vercel's Accessibility Audit Tool

The skill claims its enforced rules match what Vercel's toolbar checks.
This page is about where that claim is exact, where it's approximate,
and where it doesn't hold at all.

## The exact part

The pre-push and CI layers run `@axe-core/cli` with the WCAG 2.0/2.1
A and AA tags:

```
--tags wcag2a,wcag2aa,wcag21a,wcag21aa
```

Vercel's documentation confirms its toolbar uses the same axe-core engine
with the same WCAG 2.0 A/AA scope, grouping findings by axe's impact
ratings (critical, serious, moderate, minor). Same engine, same rule set,
same severity buckets. Findings produced by either tool against the same
page should match, modulo timing differences (something animating between
two scans, for instance).

The pre-commit layer also enforces the same axe-core rule names and
impact buckets, but it sees source rather than the rendered DOM. A
missing `alt` attribute fires the same `image-alt` rule with the same
`critical` impact in both tools. The mechanism differs, the rule doesn't.

## Where parity is approximate

The toolbar's "record" mode lets you record interactions (hover, focus,
opening a dialog) and re-runs axe-core after each one to catch issues
that only appear in those states. Our gate doesn't simulate
interactions. The CI layer scans default page load only.

If you have UI states only reachable through interaction (a hover-only
tooltip, a modal triggered by click), those don't get checked by the
gate unless your tests drive them somehow. See
[How to audit authenticated routes](../how-to/authenticated-routes.md)
for the Playwright pattern that handles this.

There's also a scoping difference. Our gate scans a fixed list of routes
(`.icansee/routes.json`). Vercel's toolbar runs against whatever page
you're on. If you keep adding pages without updating the routes file,
the gate's coverage drifts behind the toolbar's.

## Where parity doesn't hold

Single-page-app navigation behaves differently. The toolbar runs in your
live SPA and re-checks as you navigate client-side. `@axe-core/cli`
issues a fresh page load for each URL in `routes.json`. If your SPA only
has fully-functional content after client hydration that depends on
persisted state, the toolbar may see something the CLI doesn't.
Workaround: ensure each route loads cleanly from a cold visit.

Browser-specific issues are also out of scope. `@axe-core/cli` runs in a
single Puppeteer-controlled Chromium. The toolbar runs in whatever
browser the user has open. Browser-specific bugs like focus-state quirks
in Safari are outside axe-core's scope by design, and neither tool
catches them reliably.

axe-core's experimental and best-practice rules are also handled
differently. The skill enables only A/AA rule tags. axe-core has
experimental rules and best-practice rules that aren't WCAG-compliance
per se but are useful (`heading-order`, `landmark-one-main`). Vercel's
toolbar may surface these by default; our gate doesn't, because we want
every blocked commit to map to an actual WCAG success criterion.

You can broaden the tag list if you want. Edit
`templates/github-workflow-a11y.yml` and the call inside
`scripts/rendered_audit.sh` to add `best-practice` or other tags. But
once you do, you've left strict WCAG A/AA territory.

## The honest summary

For the rule classes the skill enforces (WCAG 2.0/2.1 Level A and AA), a
clean run of the icansee gate gives you the same compliance signal as a
clean Vercel toolbar audit on default page load. The gate adds:

- Source-level checks that catch issues earlier (pre-commit).
- Enforcement at the merge boundary (CI).
- Local pre-push enforcement that doesn't depend on CI.

The toolbar adds:

- Interaction recording for hover and focus states.
- Continuous on-page scanning during development.

The two are complementary tools, not competitors. Both target the same
rule set. Use them together. The gate enforces compliance at code
boundaries. The toolbar gives feedback during interactive design work.
