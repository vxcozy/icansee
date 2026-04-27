// icansee — Angular template accessibility rules.
// Plugins: @angular-eslint/eslint-plugin-template + the bundled accessibility
// rules. Mapped to WCAG 2.1 A/AA.

import angularTemplate from "@angular-eslint/eslint-plugin-template";
import angularTemplateParser from "@angular-eslint/template-parser";

export default [
  {
    files: ["**/*.component.html", "**/*.html"],
    languageOptions: { parser: angularTemplateParser },
    plugins: { "@angular-eslint/template": angularTemplate },
    rules: {
      "@angular-eslint/template/alt-text": "error",
      "@angular-eslint/template/click-events-have-key-events": "error",
      "@angular-eslint/template/elements-content": "error",
      "@angular-eslint/template/interactive-supports-focus": "error",
      "@angular-eslint/template/label-has-associated-control": "error",
      "@angular-eslint/template/mouse-events-have-key-events": "error",
      "@angular-eslint/template/no-autofocus": "error",
      "@angular-eslint/template/no-distracting-elements": "error",
      "@angular-eslint/template/no-positive-tabindex": "error",
      "@angular-eslint/template/role-has-required-aria": "error",
      "@angular-eslint/template/table-scope": "error",
      "@angular-eslint/template/valid-aria": "error",
    },
  },
];
