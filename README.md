# icansee

A Claude Code skill that installs a three-layer WCAG 2.1 A/AA
accessibility gate into your project. Same axe-core rule set as Vercel's
Accessibility Audit Tool. Blocks commits and pushes with a11y issues
before they ship.

## What it does

Three enforcement points, each catching a class of issue the others
can't:

| Layer       | Trigger        | Catches                                                                | Speed     |
| ----------- | -------------- | ---------------------------------------------------------------------- | --------- |
| Pre-commit  | `git commit`   | Source-level violations: missing alt, no label, bad ARIA, palette failures. | ~1–3s     |
| Pre-push    | `git push`     | Rendered-DOM rules via `@axe-core/cli` against the built site.         | ~30–90s   |
| CI          | PR / push      | Same as pre-push, enforced server-side. `--no-verify` cannot bypass.   | ~1–5min   |

Static checks support React, Next.js, Solid, Preact, Vue, Nuxt, Svelte,
SvelteKit, Angular, Astro, and plain HTML. The rendered audit is
framework-agnostic; it runs against whatever you build and serve.

## Install

The skill lives at `~/.claude/skills/icansee/`:

```bash
git clone https://github.com/vxcozy/icansee.git ~/.claude/skills/icansee
```

Or symlink from a development checkout:

```bash
ln -s /path/to/your/checkout ~/.claude/skills/icansee
```

See [docs/how-to/install-the-icansee-skill.md](docs/how-to/install-the-icansee-skill.md)
for symlink, project-scoped, and skills.sh installation paths.

## Use

Inside any git repo you want to gate:

```bash
~/.claude/skills/icansee/scripts/install.sh
```

The installer detects your framework(s), installs the right ESLint
plugin(s) as devDependencies, drops flat-config files into `.icansee/`,
wires the pre-commit and pre-push hooks (husky if present, plain git
hooks otherwise), and copies a GitHub Actions workflow.

To opt out of any layer:

```bash
~/.claude/skills/icansee/scripts/install.sh --no-pre-push   # skip the rendered audit hook
~/.claude/skills/icansee/scripts/install.sh --no-ci         # skip the GH workflow
~/.claude/skills/icansee/scripts/install.sh --no-hook       # skip the pre-commit hook
```

## Try it in 10 minutes

The [getting-started tutorial](docs/tutorials/getting-started.md) walks
you through installing the gate in a sandbox project, watching it block a
broken commit, fixing the issue, and seeing it pass.

## Quick examples

Check a contrast pair without installing anything:

```bash
~/.claude/skills/icansee/scripts/contrast.py check "#777" "#fff" --human
# #777 on #fff: 4.48:1 ... AA normal FAIL, AA large PASS, ...
```

Get a hue-preserving suggestion that meets AAA:

```bash
~/.claude/skills/icansee/scripts/contrast.py suggest "#777" "#fff" --target 7.0
# {"suggested": "#595959", "suggested_ratio": 7.0}
```

Audit a palette of design tokens:

```bash
~/.claude/skills/icansee/scripts/palette_audit.py matrix tokens.json
```

## Documentation

Full docs are in [`docs/`](docs/), organized via the
[Diátaxis](https://diataxis.fr) framework:

- [Tutorials](docs/tutorials/) for learning the skill
- [How-to guides](docs/how-to/) for specific tasks
- [Reference](docs/reference/) for looking up flags, env vars, exit
  codes, and rules
- [Explanation](docs/explanation/) for design rationale

Start at [docs/README.md](docs/README.md).

## How icansee differs from running axe-core directly

axe-core is the engine; icansee is the operating envelope around it.
Specifically:

- **Pre-commit static checks** that fire before code is committed,
  without needing a build or browser.
- **Pre-push rendered checks** that close the rendered-DOM gap locally
  before code leaves your machine.
- **CI enforcement** at the merge boundary so `--no-verify` can't slip
  past.
- **Framework detection** so the right ESLint plugin runs for each file
  type without manual config.
- **Idempotent installer** that translates the same setup across
  React/Vue/Svelte/Angular/Astro projects.

The rule set comes from axe-core. The shape of the gate is icansee's.

## Compatibility

- Claude Code as a SKILL.md skill.
- skills.sh marketplace format.
- macOS and Linux for the installer scripts (`bash` + `python3` 3.8+).
- Node 18+ in the project being gated, for the ESLint and `@axe-core/cli`
  layers.

## License

MIT. See [LICENSE](LICENSE).

## Credits

Built on [axe-core](https://github.com/dequelabs/axe-core) by Deque
Systems. Documentation organized via the
[Diátaxis](https://diataxis.fr) framework.
