# Known limitations

This page exists so you know when a clean icansee run is not the same as
"this page is accessible." The gate catches a large class of WCAG A/AA
issues automatically, but parts of the spec are out of reach for any
static analyzer or headless axe-core run. Reach for manual auditing
when your work touches the categories below.

## Pre-commit (static) layer

### `html_audit.py` parser limits

The static HTML check uses Python's stdlib `html.parser` rather than a
full HTML5 parser like `lxml` or `html5lib`. It's forgiving but not
spec-compliant, and that shows up in a few ways:

- Self-closing tag forms behave as you'd expect: `<img />` works, bare
  `<img>` works. Malformed nesting like `<p><div></p></div>` collapses
  unpredictably and findings on those elements may be misattributed or
  dropped.
- The `role="img"` SVG check looks for the substring `<title>` inside
  the element's accumulated text buffer rather than walking the parsed
  child tree. If a `<title>` is wrapped in another element or split
  across attributes, the check may report a false negative.
- Form-field label association is resolved at end-of-document. The gate
  sees raw HTML, not the rendered tree, so a React or Vue component
  that renders a `Label` child of an `Input` ancestor at runtime is
  invisible to this layer. Use the framework ESLint plugin (which sees
  the JSX or template) for those cases, or rely on the pre-push
  rendered audit.

### Framework ESLint plugin gaps

Each plugin has its own blind spots:

- `eslint-plugin-jsx-a11y` does not track refs across components. A
  `<Button>` that wraps `<Icon>` with the icon-only-button pattern
  passes the plugin's checks because the plugin sees `<Button>` as an
  opaque component.
- `eslint-plugin-vuejs-accessibility` works on template syntax. Content
  injected at runtime via `v-html` is outside its view.
- Conditional rendering like `{condition && <thing />}` is treated as
  always-rendered. A finding inside a branch that never actually
  renders in production still blocks the commit, and a violation only
  reachable through a specific runtime branch may be missed depending
  on how the JSX is shaped.

### Standalone unlabeled inputs (jsx-a11y, Vue, Astro)

The static layer does not catch a standalone `<input>` that has no
`<label>` anywhere near it. The `jsx-a11y/label-has-associated-control`
rule (and its Vue and Astro equivalents) fires when a `<label>` exists
but is missing its association to a control. It does not fire on an
`<input>` that is genuinely on its own with no label nearby.

This is intentional in the upstream rule: a label and its input can be
in completely different components and still associate at runtime, so
flagging "every input must have a label" would have a high false
positive rate. icansee inherits that decision.

The pre-push and CI layers (axe-core in the rendered DOM) catch the
same case correctly because by the time the DOM is rendered, either
the label is there or it isn't. So the gate as a whole still blocks
unlabeled inputs at push time. They just sail through pre-commit.

### Design tokens

`palette_audit.py` only audits the explicit foreground/background pairs
listed in `.icansee/palette.json`. If you add a new color token to your
design system but never list it as either side of a contrast pair, the
matrix audit cannot see it. The token will pass through the gate
unchecked.

The fix is to keep `palette.json` in sync with the design system. See
[How to audit design tokens for contrast](../how-to/audit-design-tokens.md).

## Pre-push (rendered) layer

### Default page load only

The pre-push hook and the CI workflow both run Playwright +
`@axe-core/playwright` against the route's initial render (per
configured color mode). They do not exercise:

- Hover states.
- Keyboard focus states beyond what's present at load.
- Dialog-open or menu-open states.
- Error states (form submission with invalid input, failed network
  requests).
- Anything else reachable only through interaction.

Vercel's toolbar has a "record interactions" mode that re-runs axe-core
after each interaction in a recorded session. The icansee gate has no
equivalent. To cover interactive states, fork
`.icansee/axe-runner.mjs` into a Playwright spec that drives the
interactions explicitly before calling `AxeBuilder`.

### SPA navigation and hydration

Each route in `.icansee/routes.json` is loaded as a fresh page visit.
Single-page-app navigation that mutates the DOM client-side, persisted
state from prior visits, and content that only appears after a specific
hydration sequence may all behave differently from what the cold load
shows. If your app's a11y characteristics depend on the navigation
path, the gate will not catch issues that only appear mid-flow.

### Manual `.dark` toggles

Color-mode emulation only flips `prefers-color-scheme`. If your site
uses a manual `.dark` class toggle (driven by JS, a cookie, or
localStorage) that does not consult `prefers-color-scheme`, the runner
won't see your dark theme even with `"modes": ["light", "dark"]`. Two
workarounds:

- Make the toggle URL-controlled (`/?theme=dark`) and list both URLs in
  `routes`. Each URL gets a full audit at the configured modes.
- Have the CSS read `prefers-color-scheme: dark` (e.g. via a
  `data-theme="auto"` default). Emulation will then take effect.

### Authentication walls

The bundled runner does not sign in. Routes behind authentication are
out of reach unless one of these is true:

- The app supports a test-mode bypass that lets the headless browser
  hit the route without credentials.
- You fork `.icansee/axe-runner.mjs` into a Playwright spec that signs
  in first. See
  [How to audit authenticated routes](../how-to/authenticated-routes.md).

### Browser-specific issues

The runner uses Playwright's bundled Chromium. Issues that only appear
in Safari, Firefox, or specific browser versions (Safari focus-ring
quirks, for instance) are outside axe-core's scope and outside what the
gate can detect. (Playwright supports WebKit and Firefox engines too;
extending the runner to sweep them is a fork-friendly change.)

## Things axe-core itself can't check

Even on the rendered DOM with full interaction recording, axe-core has
fundamental limits. These rules require human judgment, not pattern
matching:

- **Quality of alt text.** `alt="image"` satisfies the rule that
  requires `alt` to be present. To a screen reader user, it conveys
  nothing useful. The same applies to `alt="picture"`, `alt="photo"`,
  filenames left in as alt text, and decorative-but-not-marked-decorative
  patterns.
- **Caption fidelity.** Whether captions match the audio track, whether
  speaker labels are correct, whether sound effects are described.
  axe-core can confirm that a `<track>` element exists. It cannot
  confirm the file's contents are right.
- **Color as the only signal, in context.** axe-core checks contrast
  ratios. It cannot tell whether a chart uses red and green as the only
  way to distinguish two series, or whether a "required field" is shown
  only by changing the label color.
- **Heading narrative.** axe-core can verify heading levels don't skip,
  but it cannot tell whether the headings actually describe the
  content's structure or whether the page makes sense when read by
  heading alone.
- **Link text in context.** "Click here" passes the link-name rule
  (the link has accessible text). It fails the WCAG criterion that
  links be descriptive in context. That distinction needs a human.
- **Reading order.** Whether the visual order matches the DOM order in
  ways that affect comprehension.

These belong to a screen reader test pass and a manual WCAG review,
not a CI gate.

## Where to compensate

For the categories above, plan a manual auditing pass before launch and
on significant UI changes:

- Run a screen reader through your flagship flows. NVDA on Windows
  (free) and VoiceOver on macOS (built in) are the two most common
  starting points. WebAIM's [Designing for Screen Reader
  Compatibility](https://webaim.org/techniques/screenreader/) covers
  what to listen for.
- Use Deque's [WCAG 2.2 Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/)
  to walk the success criteria the gate cannot enforce. The
  understanding-level link under each criterion explains what a
  conforming implementation looks like.
- Read the [WebAIM articles](https://webaim.org/articles/) for guidance
  on alt text quality, color usage, and accessible naming patterns.
- For interactive states, recreate them with `@axe-core/playwright` in
  a Playwright test if they're stable enough to script. For everything
  else, the Vercel toolbar's record mode and a manual run-through stay
  the best option.

A clean icansee run means the source-level and default-load rendered
checks pass. It does not mean the page is accessible. It means the
mechanical rules have been satisfied and the remaining work is the work
that requires a human.
