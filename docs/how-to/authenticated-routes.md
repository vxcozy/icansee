# How to audit authenticated routes

`@axe-core/cli` can't log in for you. If your app's interesting surface is
behind authentication, the default flow won't reach it. Three ways out,
ordered by effort.

## Option 1: audit the unauthenticated shell only

For most teams this is enough. Sign-in, sign-up, password reset, marketing
pages, and the public landing surface contain the bulk of the contrast and
form-label issues that this gate is best at catching.

Leave `routes.json` pointed at unauthenticated paths and accept the
coverage gap. Add a backlog item to revisit when it bites.

## Option 2: bypass auth in the test environment

If your auth layer supports a test-mode token or a pre-shared cookie, set
it up so the local + CI builds skip the login wall:

1. Add an env var like `ICANSEE_AUTH_BYPASS=true` to the icansee env.
2. Wire your auth middleware to honor it (only when the build is the test
   build, not in prod).
3. Optionally seed a test user/session at startup.

Then `routes.json` can include authenticated paths and the gate will reach
them on the bypass session.

This is the cleanest fit if you already have a test-mode auth path for
e2e tests, since you're piggybacking on existing infrastructure.

## Option 3: switch to Playwright + @axe-core/playwright

When you outgrow `@axe-core/cli`, replace the CI workflow's run with a
Playwright spec that signs in first, then runs axe against each protected
route.

```javascript
// e2e/a11y.spec.ts
import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(async ({ page }) => {
  await page.goto("/login");
  await page.fill("[name=email]", process.env.TEST_USER_EMAIL!);
  await page.fill("[name=password]", process.env.TEST_USER_PASSWORD!);
  await page.click("button[type=submit]");
  await page.waitForURL("**/dashboard");
});

const ROUTES = ["/dashboard", "/settings/profile", "/settings/team"];

for (const route of ROUTES) {
  test(`a11y: ${route}`, async ({ page }) => {
    await page.goto(route);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(results.violations).toEqual([]);
  });
}
```

Then in CI, run `npx playwright test e2e/a11y.spec.ts` instead of (or
alongside) `@axe-core/cli`.

You can keep `@axe-core/cli` for the unauthenticated routes and use
Playwright for the protected ones. The skill's CI workflow won't drive the
Playwright run. Wire it as a separate workflow step or job.

## Trade-offs

| Option              | Effort    | Coverage of auth'd routes | Maintenance                    |
| ------------------- | --------- | ------------------------- | ------------------------------ |
| Unauthenticated only | None      | None                      | None                           |
| Auth bypass         | Medium    | Full                      | Keep bypass alive in test env  |
| Playwright + axe    | Higher    | Full                      | Spec to maintain per route     |

Most teams start with Option 1, add Option 2 once they have e2e tests with
auth bypass, and reach for Option 3 only if they're already using
Playwright extensively.
