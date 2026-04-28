// icansee: Svelte accessibility rules.
//
// eslint-plugin-svelte v3 (the version shipped with Svelte 5 / SvelteKit
// 2) consolidated all standalone `svelte/a11y-*` rules into the Svelte
// compiler's own warnings, surfaced through `svelte/valid-compile`.
// That rule reports every Svelte compile warning, including all the
// a11y_* warnings (a11y_missing_attribute, a11y_label_has_associated_control,
// a11y_click_events_have_key_events, etc.).
//
// Setting `ignoreWarnings: false` makes the rule treat compiler warnings
// as ESLint errors, so the gate fires on the same a11y issues the v2
// plugin used to report by name.

import svelte from "eslint-plugin-svelte";
import svelteParser from "svelte-eslint-parser";
import tsParser from "@typescript-eslint/parser";

export default [
  ...svelte.configs.recommended,
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
      // Treat every Svelte compiler warning, including a11y_* warnings,
      // as an ESLint error.
      "svelte/valid-compile": ["error", { ignoreWarnings: false }],
    },
  },
];
