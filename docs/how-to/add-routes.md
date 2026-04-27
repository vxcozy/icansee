# How to add routes to the rendered audit

The pre-push hook and the CI workflow both scan the routes listed in
`.icansee/routes.json`. The default is `["/"]`, which only checks the
homepage. You almost certainly want more.

## When to do this

- You just installed icansee and the audit is only checking `/`.
- You shipped a new page and the audit isn't covering it.
- You're seeing rendered-DOM issues in production but the gate didn't catch them.

## Steps

1. Open `.icansee/routes.json`. It's a flat JSON array of paths.

2. Add the routes you care about, anything that represents a
   meaningfully distinct UI surface.

   ```json
   [
     "/",
     "/about",
     "/pricing",
     "/dashboard",
     "/settings/profile",
     "/settings/team"
   ]
   ```

3. Commit the file. The next push will scan the new routes.

## Verify

Run the rendered audit locally:

```bash
~/.claude/skills/icansee/scripts/rendered_audit.sh
```

You should see one `axe-core: <URL>` block per route. If a route 404s,
axe-core will report that. Fix the path or remove the entry.

## Choosing which routes to add

You don't need to enumerate every URL. Pick routes that exercise visually
or structurally distinct UI:

- Different layouts (marketing site vs. app shell vs. settings panel).
- Different component groups (forms, tables, modals, charts).
- Pages with the most user-facing copy.

Skip near-duplicates. Two settings sub-pages built from the same components
will produce near-identical findings.

## Routes that need data

If a route requires a logged-in user, see
[How to handle authenticated routes](authenticated-routes.md).

If a route needs URL parameters (`/users/:id`), pick a representative one
and hard-code it:

```json
["/users/123", "/orders/abc"]
```

The audit doesn't traverse. It scans the URLs you list.

## Why this format

`routes.json` is a plain JSON array on purpose: it's editable by hand, by
scripts, and by the CI workflow's shell parser. There's no schema to learn.
