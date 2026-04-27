# How to use a CI provider other than GitHub Actions

The default install drops `.github/workflows/a11y.yml`. If your CI lives
elsewhere, the YAML wrapper differs but the steps don't. Install,
build, serve, run `@axe-core/cli` against routes from
`.icansee/routes.json`.

## GitLab CI

`.gitlab-ci.yml`:

```yaml
a11y:
  image: node:20
  before_script:
    - apt-get update && apt-get install -y python3
  script:
    - npm ci
    - npm run build
    - SERVE_CMD="${SERVE_CMD:-npm start}"
    - $SERVE_CMD &
    - npx --yes wait-on "${BASE_URL:-http://localhost:3000}" --timeout 60000
    - |
      ROUTES=$(cat .icansee/routes.json | python3 -c 'import json,sys; print(" ".join(json.load(sys.stdin)))')
      for r in $ROUTES; do
        npx --yes @axe-core/cli "${BASE_URL:-http://localhost:3000}$r" \
          --tags wcag2a,wcag2aa,wcag21a,wcag21aa --exit
      done
```

Delete `.github/workflows/a11y.yml` after setting this up.

## CircleCI

`.circleci/config.yml`:

```yaml
version: 2.1
jobs:
  a11y:
    docker: [{ image: cimg/node:20.0 }]
    steps:
      - checkout
      - run: npm ci
      - run: npm run build
      - run:
          name: Run axe-core
          command: |
            ${SERVE_CMD:-npm start} &
            npx --yes wait-on "${BASE_URL:-http://localhost:3000}" --timeout 60000
            ROUTES=$(cat .icansee/routes.json | python3 -c 'import json,sys; print(" ".join(json.load(sys.stdin)))')
            for r in $ROUTES; do
              npx --yes @axe-core/cli "${BASE_URL:-http://localhost:3000}$r" \
                --tags wcag2a,wcag2aa,wcag21a,wcag21aa --exit
            done
workflows:
  ci:
    jobs: [a11y]
```

## Bitbucket Pipelines

`bitbucket-pipelines.yml`:

```yaml
image: node:20
pipelines:
  default:
    - step:
        name: a11y
        script:
          - apt-get update && apt-get install -y python3
          - npm ci
          - npm run build
          - "${SERVE_CMD:-npm start} &"
          - npx --yes wait-on "${BASE_URL:-http://localhost:3000}" --timeout 60000
          - |
            ROUTES=$(cat .icansee/routes.json | python3 -c 'import json,sys; print(" ".join(json.load(sys.stdin)))')
            for r in $ROUTES; do
              npx --yes @axe-core/cli "${BASE_URL:-http://localhost:3000}$r" \
                --tags wcag2a,wcag2aa,wcag21a,wcag21aa --exit
            done
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
npm run build
${SERVE_CMD:-npm start} &
npx --yes wait-on "${BASE_URL:-http://localhost:3000}" --timeout 60000
ROUTES=$(cat .icansee/routes.json | python3 -c 'import json,sys; print(" ".join(json.load(sys.stdin)))')
for r in $ROUTES; do
  npx --yes @axe-core/cli "${BASE_URL:-http://localhost:3000}$r" \
    --tags wcag2a,wcag2aa,wcag21a,wcag21aa --exit
done
```

Wrap that in whatever your provider expects. The contract is exit non-zero
on any axe finding.

## Cleanup

After moving the workflow to your CI of choice, remove the GitHub one:

```bash
rm .github/workflows/a11y.yml
```

Re-running `install.sh` would put it back. Use `install.sh --no-ci` next
time you re-install.
