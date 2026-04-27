# Reference: environment variables

Every env var the gate reads, where it's read, and its default.

## How values are resolved

The rendered audit (`rendered_audit.sh`) reads values in this order:

1. Shell environment of the calling process.
2. `.icansee/env` (sourced via `set -a && source .icansee/env && set +a`).
3. Auto-detection from `package.json` and the filesystem.

Values from earlier sources override later ones. Set in shell to override
project defaults; set in `.icansee/env` to set project defaults; rely on
auto-detection if neither is set.

## Variables

### `BUILD_CMD`

Command to build the project before serving. Read by
`rendered_audit.sh`.

| State                 | Value                                            |
| --------------------- | ------------------------------------------------ |
| Auto-detected         | `npm run build` if `package.json` has a `build` script. Empty otherwise. |
| Override              | Any shell command. Set to `""` to skip the build entirely. |

### `SERVE_CMD`

Command to start the app. Run in the background; `kill`ed on exit.

| State                 | Value                                                     |
| --------------------- | --------------------------------------------------------- |
| Auto-detected         | First of: `npm start` (if `scripts.start`), `npm run preview` (if `scripts.preview`), `npx --yes serve -s . -p 3000`. |
| Override              | Any shell command that starts a server in the foreground. |

### `BASE_URL`

URL the audit will scan. Routes from `.icansee/routes.json` are appended
to this.

| State                 | Value                          |
| --------------------- | ------------------------------ |
| Default               | `http://localhost:3000`        |
| Override              | Any URL.                       |

### `WAIT_TIMEOUT`

Milliseconds to wait for `BASE_URL` to respond before failing the audit.

| State                 | Value     |
| --------------------- | --------- |
| Default               | `60000`   |
| Override              | Any positive integer. Slow builds may want `120000` or higher. |

### CI workflow specific

The GH Actions workflow honors two more variables, set as repository or
organization variables in GitHub's settings:

| Variable                | Effect                                                  |
| ----------------------- | ------------------------------------------------------- |
| `ICANSEE_BASE_URL`      | Sets `BASE_URL` for the workflow run.                   |
| `ICANSEE_SERVE_CMD`     | Sets `SERVE_CMD` for the workflow run.                  |

Set them in **Settings → Secrets and variables → Actions → Variables**.
They become `vars.ICANSEE_BASE_URL` etc. in the workflow file.

## Variables NOT read

For reference, things you might think the skill reads but doesn't:

- `NODE_ENV`: not consulted. `BUILD_CMD` and `SERVE_CMD` carry that
  intent.
- `PORT`: set the port via `SERVE_CMD` (e.g., `npm start -- --port 4000`)
  and update `BASE_URL` to match.
- `CI`: the workflow is the same whether or not `CI=true` is set.

## Verifying which values are in effect

```bash
( cd <repo> && [ -f .icansee/env ] && source .icansee/env; \
  echo "BUILD_CMD=${BUILD_CMD-<auto>}"; \
  echo "SERVE_CMD=${SERVE_CMD-<auto>}"; \
  echo "BASE_URL=${BASE_URL:-http://localhost:3000}"; \
  echo "WAIT_TIMEOUT=${WAIT_TIMEOUT:-60000}" )
```
