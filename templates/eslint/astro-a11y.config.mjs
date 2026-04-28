// icansee: Astro accessibility rules.
//
// `eslint-plugin-astro` ships its own `jsx-a11y-strict` config that already
// enables every relevant jsx-a11y rule under the `astro/jsx-a11y/*`
// namespace, configured for Astro's HTML-style template attributes (`for`
// rather than `htmlFor`, etc.). Re-registering the `jsx-a11y` plugin
// alongside it caused duplicate findings AND triggered false positives on
// the canonical `<label for="x">` + `<input id="x">` sibling pattern,
// because the upstream jsx-a11y rule expects JSX's `htmlFor` attribute
// name. We rely on the Astro-namespaced version instead.

import astro from "eslint-plugin-astro";

export default [
  ...astro.configs.recommended,
  ...astro.configs["jsx-a11y-strict"],
];
