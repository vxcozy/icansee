// icansee: Astro accessibility rules.
// Plugin: eslint-plugin-astro (which composes jsx-a11y for Astro's JSX-y
// templates). Mapped to WCAG 2.1 A/AA.

import astro from "eslint-plugin-astro";
import jsxA11y from "eslint-plugin-jsx-a11y";

export default [
  ...astro.configs.recommended,
  ...astro.configs["jsx-a11y-strict"],
  {
    files: ["**/*.astro"],
    plugins: { "jsx-a11y": jsxA11y },
    rules: {
      // Astro re-exports jsx-a11y rules under the same names.
      "jsx-a11y/alt-text": "error",
      "jsx-a11y/anchor-has-content": "error",
      "jsx-a11y/anchor-is-valid": "error",
      "jsx-a11y/aria-props": "error",
      "jsx-a11y/aria-role": "error",
      "jsx-a11y/heading-has-content": "error",
      "jsx-a11y/html-has-lang": "error",
      "jsx-a11y/iframe-has-title": "error",
      "jsx-a11y/label-has-associated-control": "error",
      "jsx-a11y/no-autofocus": "error",
      "jsx-a11y/no-distracting-elements": "error",
      "jsx-a11y/role-has-required-aria-props": "error",
      "jsx-a11y/tabindex-no-positive": "error",
    },
  },
];
