#!/usr/bin/env node
// icansee: rendered-DOM accessibility audit, Playwright + axe-core.
//
// Walks every route in .icansee/routes.json across every configured color
// mode (light / dark), emulating `prefers-color-scheme` per scan. Same rule
// set as the Vercel Accessibility Audit Tool: WCAG 2.0 + 2.1 A and AA.
//
// Invoked by scripts/rendered_audit.sh and the GitHub Actions workflow.
// Reads BASE_URL from the environment (default http://localhost:3000) and
// expects the app to already be served there.
//
// Schema for .icansee/routes.json is defined and validated in
// parse-routes.mjs (alongside this file once installed).
//
// Exit codes:
//   0  clean
//   1  one or more axe violations
//   2  infra error (bad config, page wouldn't load, browser missing)

import process from "node:process";
import { chromium } from "playwright";
import AxeBuilder from "@axe-core/playwright";
import { loadConfig } from "./parse-routes.mjs";

const BASE_URL = (process.env.BASE_URL || "http://localhost:3000").replace(/\/$/, "");
const ROUTES_PATH = process.env.ICANSEE_ROUTES_JSON || ".icansee/routes.json";

const { routes, modes } = loadConfig(ROUTES_PATH);

const bold = (s) => `\x1b[1m${s}\x1b[0m`;

let browser;
try {
  browser = await chromium.launch();
} catch (e) {
  console.error("icansee: failed to launch chromium. Try `npx playwright install chromium`.");
  console.error(`        (${e.message})`);
  process.exit(2);
}

let totalViolations = 0;
let infraError = false;

try {
  for (const route of routes) {
    for (const mode of modes) {
      const url = `${BASE_URL}${route}`;
      console.log(`\n${bold(`▸ axe: ${url} [${mode}]`)}`);
      const ctx = await browser.newContext({ colorScheme: mode });
      const page = await ctx.newPage();
      try {
        await page.goto(url, { waitUntil: "load", timeout: 30000 });
      } catch (e) {
        console.error(`  ✗ failed to load ${url}: ${e.message}`);
        infraError = true;
        await ctx.close();
        continue;
      }
      let results;
      try {
        results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
          .analyze();
      } catch (e) {
        console.error(`  ✗ axe failed on ${url}: ${e.message}`);
        infraError = true;
        await ctx.close();
        continue;
      }
      if (results.violations.length === 0) {
        console.log(`  ✓ no violations`);
      } else {
        totalViolations += results.violations.length;
        for (const v of results.violations) {
          console.log(`  ✗ [${v.id}] ${v.help}${v.impact ? ` (${v.impact})` : ""}`);
          console.log(`    ${v.helpUrl}`);
          for (const node of v.nodes.slice(0, 5)) {
            const target = Array.isArray(node.target) ? node.target.join(" ") : String(node.target);
            console.log(`    - ${target}`);
            if (node.failureSummary) {
              for (const line of node.failureSummary.split("\n").slice(0, 3)) {
                console.log(`        ${line}`);
              }
            }
          }
          if (v.nodes.length > 5) {
            console.log(`    ... and ${v.nodes.length - 5} more node(s)`);
          }
        }
      }
      await ctx.close();
    }
  }
} finally {
  await browser.close();
}

const summary = `${routes.length} route(s) × ${modes.length} mode(s)`;

if (infraError) {
  console.error(`\nicansee: ✗ infra error during rendered audit (${summary})`);
  process.exit(2);
}
if (totalViolations > 0) {
  console.log(`\nicansee: ✗ ${totalViolations} accessibility violation(s) across ${summary}`);
  console.log(`        Fix the issues above. To bypass (not recommended):`);
  console.log(`        git push --no-verify`);
  process.exit(1);
}
console.log(`\nicansee: ✓ rendered-DOM audit clean across ${summary}`);
process.exit(0);
