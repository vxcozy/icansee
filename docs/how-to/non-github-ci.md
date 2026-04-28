# How to use a CI provider other than GitHub Actions

The default install drops `.github/workflows/a11y.yml`. If your CI lives
elsewhere, the YAML wrapper differs but the steps don't. Install deps,
install Playwright's chromium, build, serve, hand off to
`.icansee/axe-runner.mjs` (which iterates routes × color modes from
`.icansee/routes.json`).

The Microsoft-published Playwright base image
(`mcr.microsoft.com/playwright:v1.48.0-jammy`) ships chromium and its OS
libraries preinstalled. If you stick with a plain `node:20` image, add
`npx playwright install --with-deps chromium` to install them on
demand.

## GitLab CI

`.gitlab-ci.yml`:

```yaml
a11y:
  image: mcr.microsoft.com/playwright:v1.48.0-jammy
  script:
    - npm ci
    - npm install --prefix .icansee --no-audit --no-fund
    - cd .icansee && npx playwright install chromium && cd -
    - npm run build
    - SERVE_CMD="${SERVE_CMD:-npm start}"
    - $SERVE_CMD &
    - npx --yes wait-on "${BASE_URL:-http://localhost:3000}" --timeout 60000
    - BASE_URL="${BASE_URL:-http://localhost:3000}" node .icansee/axe-runner.mjs
```

Delete `.github/workflows/a11y.yml` after setting this up.

## CircleCI

`.circleci/config.yml`:

```yaml
version: 2.1
jobs:
  a11y:
    docker: [{ image: mcr.microsoft.com/playwright:v1.48.0-jammy }]
    steps:
      - checkout
      - run: npm ci
      - run: npm install --prefix .icansee --no-audit --no-fund
      - run: cd .icansee && npx playwright install chromium
      - run: npm run build
      - run:
          name: Run rendered audit
          command: |
            ${SERVE_CMD:-npm start} &
            npx --yes wait-on "${BASE_URL:-http://localhost:3000}" --timeout 60000
            BASE_URL="${BASE_URL:-http://localhost:3000}" node .icansee/axe-runner.mjs
workflows:
  ci:
    jobs: [a11y]
```

## Bitbucket Pipelines

`bitbucket-pipelines.yml`:

```yaml
image: mcr.microsoft.com/playwright:v1.48.0-jammy
pipelines:
  default:
    - step:
        name: a11y
        script:
          - npm ci
          - npm install --prefix .icansee --no-audit --no-fund
          - cd .icansee && npx playwright install chromium && cd -
          - npm run build
          - "${SERVE_CMD:-npm start} &"
          - npx --yes wait-on "${BASE_URL:-http://localhost:3000}" --timeout 60000
          - BASE_URL="${BASE_URL:-http://localhost:3000}" node .icansee/axe-runner.mjs
```

## Vercel

If your project is deployed via Vercel, you don't need a separate CI
workflow at all. Enable the "Accessibility Audit" permission on your
Vercel toolbar and it runs the same axe-core checks against every preview
deployment. Same engine, different surfacing.

The pre-commit and pre-push layers from icansee still run locally and
give earlier feedback than waiting for Vercel to deploy.

## Generic shell

If your CI is something else, the underlying shell script is short:

```bash
#!/usr/bin/env bash
set -e
npm ci
npm install --prefix .icansee --no-audit --no-fund
(cd .icansee && npx playwright install --with-deps chromium)
npm run build
${SERVE_CMD:-npm start} &
npx --yes wait-on "${BASE_URL:-http://localhost:3000}" --timeout 60000
BASE_URL="${BASE_URL:-http://localhost:3000}" node .icansee/axe-runner.mjs
```

Wrap that in whatever your provider expects. The contract is exit
non-zero on any axe finding (1 for violations, 2 for infra error).

## Cleanup

After moving the workflow to your CI of choice, remove the GitHub one:

```bash
rm .github/workflows/a11y.yml
```

Re-running `install.sh` would put it back. Use `install.sh --no-ci` next
time you re-install.
