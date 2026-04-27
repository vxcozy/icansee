// icansee — Svelte accessibility rules.
// Plugin: eslint-plugin-svelte exposes Svelte compiler's a11y warnings as
// lint rules. Strict subset mapped to WCAG 2.1 A/AA.

import svelte from "eslint-plugin-svelte";
import svelteParser from "svelte-eslint-parser";
import tsParser from "@typescript-eslint/parser";

export default [
  ...svelte.configs["flat/recommended"],
  {
    files: ["**/*.svelte"],
    languageOptions: {
      parser: svelteParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: "latest",
        sourceType: "module",
        extraFileExtensions: [".svelte"],
      },
    },
    rules: {
      "svelte/a11y-accesskey": "error",
      "svelte/a11y-aria-attributes": "error",
      "svelte/a11y-autofocus": "error",
      "svelte/a11y-click-events-have-key-events": "error",
      "svelte/a11y-distracting-elements": "error",
      "svelte/a11y-figcaption-has-content": "error",
      "svelte/a11y-figcaption-parent": "error",
      "svelte/a11y-hidden": "error",
      "svelte/a11y-img-redundant-alt": "error",
      "svelte/a11y-incorrect-aria-attribute-type": "error",
      "svelte/a11y-interactive-supports-focus": "error",
      "svelte/a11y-label-has-associated-control": "error",
      "svelte/a11y-media-has-caption": "error",
      "svelte/a11y-misplaced-role": "error",
      "svelte/a11y-misplaced-scope": "error",
      "svelte/a11y-missing-attribute": "error",
      "svelte/a11y-missing-content": "error",
      "svelte/a11y-mouse-events-have-key-events": "error",
      "svelte/a11y-no-abstract-role": "error",
      "svelte/a11y-no-noninteractive-element-interactions": "error",
      "svelte/a11y-no-noninteractive-element-to-interactive-role": "error",
      "svelte/a11y-no-noninteractive-tabindex": "error",
      "svelte/a11y-no-redundant-roles": "error",
      "svelte/a11y-no-static-element-interactions": "error",
      "svelte/a11y-positive-tabindex": "error",
      "svelte/a11y-role-has-required-aria-props": "error",
      "svelte/a11y-role-supports-aria-props": "error",
      "svelte/a11y-structure": "error",
      "svelte/a11y-unknown-aria-attribute": "error",
      "svelte/a11y-unknown-role": "error",
    },
  },
];
