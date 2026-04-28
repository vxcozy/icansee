// icansee: Vue SFC accessibility rules.
// Plugin: eslint-plugin-vuejs-accessibility. Mapped to WCAG 2.1 A/AA.

import vueA11y from "eslint-plugin-vuejs-accessibility";
import vueParser from "vue-eslint-parser";
import tsParser from "@typescript-eslint/parser";

export default [
  {
    files: ["**/*.vue"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: "latest",
        sourceType: "module",
      },
    },
    plugins: { "vuejs-accessibility": vueA11y },
    rules: {
      "vuejs-accessibility/alt-text": "error",
      "vuejs-accessibility/anchor-has-content": "error",
      "vuejs-accessibility/aria-props": "error",
      "vuejs-accessibility/aria-role": "error",
      "vuejs-accessibility/aria-unsupported-elements": "error",
      "vuejs-accessibility/click-events-have-key-events": "error",
      "vuejs-accessibility/form-control-has-label": "error",
      "vuejs-accessibility/heading-has-content": "error",
      "vuejs-accessibility/iframe-has-title": "error",
      "vuejs-accessibility/interactive-supports-focus": "error",
      // `label-has-for` defaults to requiring BOTH nesting AND for/id,
      // which rejects the standard `<label for>...</label><input id>`
      // pattern. Configure to accept either approach.
      "vuejs-accessibility/label-has-for": [
        "error",
        { required: { some: ["nesting", "id"] } },
      ],
      "vuejs-accessibility/media-has-caption": "error",
      "vuejs-accessibility/mouse-events-have-key-events": "error",
      "vuejs-accessibility/no-access-key": "error",
      "vuejs-accessibility/no-autofocus": "error",
      "vuejs-accessibility/no-distracting-elements": "error",
      "vuejs-accessibility/no-onchange": "error",
      "vuejs-accessibility/no-redundant-roles": "error",
      "vuejs-accessibility/no-static-element-interactions": "error",
      "vuejs-accessibility/role-has-required-aria-props": "error",
      "vuejs-accessibility/tabindex-no-positive": "error",
    },
  },
];
