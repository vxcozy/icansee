# Why axe-core

The skill enforces the axe-core rule set rather than something custom.
Here's why, and what alternatives we considered.

## What axe-core is

axe-core is the WCAG accessibility testing engine maintained by Deque
Systems. It powers:

- Chrome DevTools' a11y panel.
- Lighthouse's accessibility audit.
- Vercel's Accessibility Audit Tool.
- VS Code's accessibility linter.
- GitHub's a11y review tooling.
- A long list of CI integrations.

Each rule maps to a specific WCAG success criterion (or, for
best-practice rules, to widely-accepted UX heuristics that aren't strictly
WCAG). The mapping is documented at
https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md.

## Why not write our own

We considered it. Three reasons we didn't.

The first is compatibility. Telling a contributor "your code fails our
custom rule 12-A" is friction. Telling them "your code fails the same
rule that DevTools, Lighthouse, and Vercel's toolbar all check" routes
them toward existing documentation, existing fixes, and existing
intuition. The rule ID becomes a search query that lands on canonical
guidance.

The second is calibration. axe-core has been tuned over a decade against
millions of real pages. Their false-positive and false-negative rates
for each rule are known. We have no way to match that calibration with
a custom rule set.

The third is maintenance. WCAG evolves. axe-core tracks WCAG changes; if
we wrote our own, we'd be tracking those changes ourselves, lagging
behind, and introducing drift between what the gate enforces and what
auditors check.

## What axe-core gets us specifically

Every rule is named and stable. `image-alt`, `button-name`,
`color-contrast` are the same identifiers across every tool.

Every rule maps to a WCAG success criterion. When the gate fires
`color-contrast`, you can point at WCAG 1.4.3 and say "this is the rule
we're enforcing."

Severity buckets are pre-calibrated. Critical, serious, moderate, minor
are meaningful because Deque assigned them based on real-world impact,
not because we made them up.

## The static layer's relationship to axe-core

`@axe-core/cli` runs against a rendered DOM, so it can't fire at
pre-commit. The static layer (`html_audit.py`, `eslint-plugin-jsx-a11y`,
the framework-specific ESLint plugins) checks the *same* rules where
they're statically detectable.

`eslint-plugin-jsx-a11y` is itself partially derived from axe-core's
rules. Same names, same intent, source-side checks where possible. We
inherit that mapping by reusing the plugin rather than reimplementing
it.

For HTML, our `html_audit.py` enforces the subset of axe-core rules
that are visible in raw HTML, using the same rule names and impact
buckets. We didn't invent those names. Output formatted as
`[critical] image-alt: <img> missing alt` is meant to look identical to
axe-core's output for the same finding.

## Alternatives we considered

Pa11y. Built on top of HTML_CodeSniffer rather than axe-core. Smaller
rule set, less commonly used in modern tooling, no Vercel parity.
Rejected.

HTML_CodeSniffer. Older, less actively maintained. Rejected.

Custom rules tuned to your design system. Tempting, but we'd have to
build and maintain them. The first version of icansee should be useful
without that investment. If you want design-system-specific rules later,
add them as a separate ESLint plugin alongside icansee. They layer
cleanly.

## When axe-core falls short

Two known limitations worth naming.

axe-core can't check every WCAG rule. Many WCAG success criteria are
about intent rather than markup. Does the audio description match the
spoken content? There's no automated way to check that. axe-core sticks
to the rules it can check reliably; manual audits are still required for
full WCAG compliance.

axe-core is conservative on contrast. It only flags clear failures. If a
foreground/background combination is ambiguous (text over an image,
gradient backgrounds, semi-transparent fg), axe-core skips it rather
than guess. The skill flags those for manual review with the same "needs
review" disposition.

We don't try to do better than axe-core here. Its calibration is the
state of the art. If a rule is wrong, the right place to fix it is
upstream.
