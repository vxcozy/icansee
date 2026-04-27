# Reference: ESLint configurations

Each framework gets a flat-config `.mjs` file that pins a strict
WCAG-aligned rule set. Configs are dropped into `.icansee/` by
`install.sh` and called from `audit.sh` via `--config`.

This page lists what each config enables. For the full rule semantics
see the upstream plugin docs (linked per section).

## File mapping

| Source file extension(s)            | Config installed                                  |
| ----------------------------------- | ------------------------------------------------- |
| `.jsx`, `.tsx`                      | `.icansee/eslint-jsx-a11y.config.mjs`             |
| `.vue`                              | `.icansee/eslint-vuejs-a11y.config.mjs`           |
| `.svelte`                           | `.icansee/eslint-svelte-a11y.config.mjs`          |
| `.component.html`, `.html` (Angular)| `.icansee/eslint-angular-template-a11y.config.mjs`|
| `.astro`                            | `.icansee/eslint-astro-a11y.config.mjs`           |

The Angular dispatch only fires when `<repo>/angular.json` exists.

## JSX / TSX (`eslint-plugin-jsx-a11y`)

Plugin: https://github.com/jsx-eslint/eslint-plugin-jsx-a11y

Starts from `jsxA11y.flatConfigs.strict`, then sets every relevant rule
to `error`:

```
alt-text, anchor-has-content, anchor-is-valid,
aria-activedescendant-has-tabindex, aria-props, aria-proptypes,
aria-role, aria-unsupported-elements, autocomplete-valid,
click-events-have-key-events, control-has-associated-label,
heading-has-content, html-has-lang, iframe-has-title,
img-redundant-alt, interactive-supports-focus,
label-has-associated-control, lang, media-has-caption,
mouse-events-have-key-events, no-access-key, no-autofocus,
no-distracting-elements,
no-interactive-element-to-noninteractive-role,
no-noninteractive-element-interactions,
no-noninteractive-element-to-interactive-role,
no-noninteractive-tabindex, no-redundant-roles,
no-static-element-interactions, role-has-required-aria-props,
role-supports-aria-props, scope, tabindex-no-positive
```

## Vue (`eslint-plugin-vuejs-accessibility`)

Plugin: https://github.com/vue-a11y/eslint-plugin-vuejs-accessibility

```
alt-text, anchor-has-content, aria-props, aria-role,
aria-unsupported-elements, click-events-have-key-events,
form-control-has-label, heading-has-content, iframe-has-title,
interactive-supports-focus, label-has-for, media-has-caption,
mouse-events-have-key-events, no-access-key, no-autofocus,
no-distracting-elements, no-onchange, no-redundant-roles,
no-static-element-interactions, role-has-required-aria-props,
tabindex-no-positive
```

Parser: `vue-eslint-parser` with `@typescript-eslint/parser` for
`<script lang="ts">`.

## Svelte (`eslint-plugin-svelte`)

Plugin: https://sveltejs.github.io/eslint-plugin-svelte/

Builds on `svelte.configs["flat/recommended"]`. Sets every `svelte/a11y-*`
rule to `error`:

```
a11y-accesskey, a11y-aria-attributes, a11y-autofocus,
a11y-click-events-have-key-events, a11y-distracting-elements,
a11y-figcaption-has-content, a11y-figcaption-parent, a11y-hidden,
a11y-img-redundant-alt, a11y-incorrect-aria-attribute-type,
a11y-interactive-supports-focus, a11y-label-has-associated-control,
a11y-media-has-caption, a11y-misplaced-role, a11y-misplaced-scope,
a11y-missing-attribute, a11y-missing-content,
a11y-mouse-events-have-key-events, a11y-no-abstract-role,
a11y-no-noninteractive-element-interactions,
a11y-no-noninteractive-element-to-interactive-role,
a11y-no-noninteractive-tabindex, a11y-no-redundant-roles,
a11y-no-static-element-interactions, a11y-positive-tabindex,
a11y-role-has-required-aria-props, a11y-role-supports-aria-props,
a11y-structure, a11y-unknown-aria-attribute, a11y-unknown-role
```

These are the same a11y warnings the Svelte compiler emits, surfaced via
ESLint so they participate in the gate.

## Angular templates (`@angular-eslint/eslint-plugin-template`)

Plugin: https://github.com/angular-eslint/angular-eslint

```
@angular-eslint/template/alt-text,
@angular-eslint/template/click-events-have-key-events,
@angular-eslint/template/elements-content,
@angular-eslint/template/interactive-supports-focus,
@angular-eslint/template/label-has-associated-control,
@angular-eslint/template/mouse-events-have-key-events,
@angular-eslint/template/no-autofocus,
@angular-eslint/template/no-distracting-elements,
@angular-eslint/template/no-positive-tabindex,
@angular-eslint/template/role-has-required-aria,
@angular-eslint/template/table-scope,
@angular-eslint/template/valid-aria
```

Parser: `@angular-eslint/template-parser`. Targets
`*.component.html` files.

## Astro (`eslint-plugin-astro` + `eslint-plugin-jsx-a11y`)

Plugin: https://ota-meshi.github.io/eslint-plugin-astro/

Composes `astro.configs.recommended` and
`astro.configs["jsx-a11y-strict"]`. Astro re-exports jsx-a11y rules
under their original names; we set the WCAG-relevant ones to `error`:

```
jsx-a11y/alt-text, jsx-a11y/anchor-has-content,
jsx-a11y/anchor-is-valid, jsx-a11y/aria-props, jsx-a11y/aria-role,
jsx-a11y/heading-has-content, jsx-a11y/html-has-lang,
jsx-a11y/iframe-has-title, jsx-a11y/label-has-associated-control,
jsx-a11y/no-autofocus, jsx-a11y/no-distracting-elements,
jsx-a11y/role-has-required-aria-props, jsx-a11y/tabindex-no-positive
```

## Customizing

Don't edit the configs in `.icansee/` directly. `install.sh` overwrites
them on re-run. If you want to customize:

1. Add or override rules in your project's own ESLint config (the one
   not under `.icansee/`).
2. Or, fork the templates in the skill at
   `templates/eslint/*.config.mjs` and re-run `install.sh` from your
   fork.

The icansee gate doesn't run your project's ESLint config. It
explicitly passes `--config <our-flat-config>`. So your custom rules
won't conflict, but they also won't participate in the gate. Use the
gate for compliance enforcement; use your own ESLint config for
project-style rules.
