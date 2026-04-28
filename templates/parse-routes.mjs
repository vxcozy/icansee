// icansee: routes.json parser. Exported so the runner imports it
// statically; runnable directly so the test suite can exercise it
// without pulling in playwright.
//
// Schema:
//
//   Legacy array form:
//     ["/", "/dashboard"]                    // light mode only
//
//   Object form (v0.3+):
//     { "routes": ["/", "/dashboard"],
//       "modes":  ["light", "dark"] }
//
// Routes must start with "/". Modes accept only "light" and "dark".

import fs from "node:fs";
import process from "node:process";

const ALLOWED_MODES = new Set(["light", "dark"]);

export function loadConfig(routesPath) {
  let routes = ["/"];
  let modes = ["light"];

  if (!fs.existsSync(routesPath)) {
    return { routes, modes };
  }

  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(routesPath, "utf8"));
  } catch (e) {
    console.error(`icansee: ${routesPath} is not valid JSON: ${e.message}`);
    process.exit(2);
  }

  if (Array.isArray(raw)) {
    routes = raw;
  } else if (raw && typeof raw === "object") {
    if (Array.isArray(raw.routes) && raw.routes.length > 0) {
      routes = raw.routes;
    }
    if (Array.isArray(raw.modes) && raw.modes.length > 0) {
      modes = raw.modes;
    }
  } else {
    console.error(`icansee: ${routesPath} must be an array or object`);
    process.exit(2);
  }

  for (const m of modes) {
    if (!ALLOWED_MODES.has(m)) {
      console.error(`icansee: invalid mode "${m}" in ${routesPath} (allowed: light, dark)`);
      process.exit(2);
    }
  }

  for (const r of routes) {
    if (typeof r !== "string") {
      console.error(`icansee: routes must be strings; got ${JSON.stringify(r)}`);
      process.exit(2);
    }
    if (!r.startsWith("/")) {
      console.error(`icansee: route "${r}" must start with "/" (e.g. "/dashboard")`);
      process.exit(2);
    }
  }

  return { routes, modes };
}

// CLI entry: `node parse-routes.mjs [path-to-routes.json]`. Prints the
// resolved {routes, modes} as JSON. Used by tests/test_runner_schema.sh.
if (import.meta.url === `file://${process.argv[1]}`) {
  const path = process.argv[2] || ".icansee/routes.json";
  const cfg = loadConfig(path);
  console.log(JSON.stringify(cfg));
}
