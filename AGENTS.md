# kailash-packages: guide for contributors and coding agents

This file is the single source of truth for humans and coding agents on
kailash-packages. The coding agents include GitHub Copilot, Claude, Cursor
and Hermes.

Tool-specific files (`CLAUDE.md`, `.github/copilot-instructions.md`) only
point here. When this file and a tool-specific file disagree, this file wins.

Read the [Manifest and taxonomy](#the-manifest-and-the-taxonomy-single-home-rule),
[Testing](#testing) and [Security](#security) sections before any change.
The rest is a map of the repository.

## Project overview

`kailash-packages` is the overlay of the
[Kailash OS](https://github.com/kailash-os/kailash-os) distribution. The
overlay is a flake-parts Nix overlay. It carries pinned upstream sources,
package derivations and the **manifest**. The manifest is the taxonomy's
single home.

The OS root flake pins this repo. Profiles in the OS repo compose categories
whose entries are defined here.

The roadmap board
([org project 1](https://github.com/orgs/kailash-os/projects/1)) carries
issue `KA-NN` items. [Issue #61](https://github.com/kailash-os/kailash-os/issues/61)
on the OS repo is the canon map. Every new roadmap item adds a row to its
dependency graph and sprint decomposition register.

## Repository structure

| Directory | Purpose |
| --- | --- |
| `flake.nix` + `flake-parts/` | The overlay flake. Carries the packages, the checks and the export consumed by the OS root flake's `kailash-packages` input |
| `manifest/` | `categories.yaml` (31-category census across CORE + CLASSIC/ATTACK/DEFENCE/OPS) and `tools.yaml` (tool inventory: ids, licences, packaging shapes, safety classes, ATLAS + standards mappings) |
| `nvfetcher/` | Upstream source pins: `config.toml` + committed `_sources/`. The regeneration tool is nvfetcher, never hand edits to `_sources` |
| `pkgs/` | Package derivations, auto-called. Bespoke (overlay-defined) tools carry a derivation path recorded in the manifest |
| `tests/` | The manifest validator (`tests/validate_manifest.py`) — the single enforcement point for manifest invariants |

## The manifest and the taxonomy (single home rule)

The taxonomy is **versioned data**, not prose. Every later artifact (modules,
profiles, menu, CLI, docs, site) generates from these two files. The
validator enforces one-tool-one-primary-category with secondary tags. Layer,
category and tool facts live here. Never duplicate them into the OS modules,
READMEs or site copy.

The census is [the spec's §2.6 post-purge table](https://github.com/kailash-os/kailash-os/blob/master/docs/spec.md#26-the-full-category-table-post-purge-census).
It records CLASSIC 141 tool slots, ATTACK about 59, DEFENCE about 46 and OPS
about 91. The C-7 SDR pack is recorded as `opt-in: data-pack`. Default
profiles and images never carry it.

The [spec
§2.7](https://github.com/kailash-os/kailash-os/blob/master/docs/spec.md#27-deliberate-exclusions)
records the deliberate exclusions. The excluded classes: no hardware/RF/wifi
tools, no paid-licence tools, no unmaintained or cloud-only tools. These
exclusions are the ("no-resurrection guard"). The manifest validator refuses
purged tooling. Do not reintroduce it.

Data-accuracy rules:

- ATLAS tactic mappings (ATTACK layer) are manifest fields with real
  identifiers. ASVS, AISVS, MLSVS and OWASP-LLM mappings (DEFENCE layer) are
  manifest fields with real identifiers. Verify each mapping against the
  public MITRE ATLAS dataset first. Never invent a technique id.
- Licences are recorded per tool in the manifest. Unfree posture is explicit
  at the flake level. Never widen it for convenience.
- Safety classes are per-tool manifest fields. `safety:exp` tooling wires the
  lab-mode gate in the OS repo. A manifest row without its safety class
  blocks the validator.

## Testing

The repo follows the
[hypothesis-first TDD standard](https://github.com/kailash-os/kailash-os/issues/51):
**spec (from the issue's plan reference) → RED (watched, committed) → GREEN →
PR**. The engineering standard also orders
[harness-before-capability](https://github.com/kailash-os/kailash-os/issues/119).
The check that gates a behaviour ships in the same PR as the behaviour. CI
proves every new gate's negative case.

- **Manifest invariants live in the validator** (`tests/validate_manifest.py`).
  The invariants: schema shape, unique ids, categories-exist, derivation-path
  presence for bespoke tools, ATLAS coverage on ATTACK tools, the
  no-resurrection guard. A new invariant extends the validator first, with
  RED. Never use an ad-hoc script.
- **Run what CI runs** before opening a PR: `nix flake check` plus the
  validator. The `flake-check` workflow is the authoritative gate. Local
  green is development evidence only.
- **No invented transcripts.** A claim about a build or validation run cites
  its real output, plus the issue or PR where the run lives. Without a run,
  mark it PENDING with the owning issue. Never approximate.

## Signing

**Everything is GPG-signed, always.** Commits and tags stay GPG-signed
(`git config commit.gpgsign true`). PR CI enforces `required_signatures`.
An unsigned or badly-attributed commit blocks the PR. The signing key and the
commit email must match a GitHub-verified identity. A mismatch fails
verification with `bad_email`, and the PR cannot merge.

## Architecture Decision Records

Structural changes carry an ADR in the same PR. Most slices are leaf-sized:
the issue's plan reference IS the design record, so no ADR is needed. Write
an ADR in these cases only. The change introduces a new persistent artifact:
a manifest schema field whose semantics lock, a profile contract, a wire
format, a gate script. Or the change removes or alters one.

The ADR home is deliberately **single**. The distribution keeps its decision
records in the OS repo's
[`docs/adr/`](https://github.com/kailash-os/kailash-os/blob/master/docs/adr/0000-architecture-decision-records.md).
See [the process](https://github.com/kailash-os/kailash-os/blob/master/docs/adr/0000-architecture-decision-records.md)
and [the record format](https://github.com/kailash-os/kailash-os/blob/master/docs/adr/0001-record-format.md).
Overlay decisions (locked manifest schema fields, nvfetcher wire formats)
land there. The PR that makes the change carries the ADR, and the index
gains its row. The hard rules:

- **Accepted ADRs are immutable.** A change that contradicts an accepted ADR
  supersedes it with a new one. Never rewrite the accepted record.
- **Never invent discussion, deciders or quotes.** Cite commit/issue
  permalinks, or write "No substantive technical discussion recorded".
- Dependency bumps, docs and CI tweaks don't need ADRs.

## Pull requests

Follow [`CONTRIBUTING.md`](CONTRIBUTING.md). Cut a leaf branch from
**current `origin/main`**. One logical change per PR. Watched RED precedes
GREEN. All commits stay GPG-signed.

Titles follow Conventional Commits. Roadmap slices carry the task id in the
subject: `type(scope): KA-XXn — summary`. Example:
`feat(pkgs): KA-12.1 — ART: pin + Shape-1 derivation`. A CI title gate checks
the form. The body links the child issue (`Closes #NN`) and notes the parent
gate stays open. The body states **what** changed, **why**, and **how
verified**.

## Labels

| Label | Meaning |
| --- | --- |
| `KA-XXn — <summary>` (issue titles carry it in the title, not a label; PR titles carry it in the conventional subject) | issue/PR identity |
| `area:manifest\|packaging\|nix\|layer-classic\|layer-attack\|layer-defence\|layer-ops\|testing\|repo\|docs\|github` | component (the current catalog) |
| `type:task` | a leaf-sized roadmap slice (RED→GREEN→merge) — the only `type:*` label in the catalog today |
| `target:v0.1\|v0.2\|backlog` | milestone |
| `s:xs\|s:s\|s:m\|s:l` | sprint effort |

Board status is an org-project **field**, not a label. Cross-repo children
never auto-close. A PR merged in this repo does not close an issue filed on
`kailash-os`. Verify the merge first. Close the OS issue there with a
("merged via <repo>#N") comment. A label-catalog growth is a deliberate
catalog change, not agent improvisation.

## Security

This overlay pins the supply chain of a distribution that packages offensive
tooling. The attack surface is the **manifest itself**:

- A tool's source URL, pin and licence are attacker-relevant data. Review
  validates every change: new `nvfetcher` names, changed pins, licence
  downgrades.
- Inputs stay pinned. The rules: committed `_sources/`, no floating refs, no
  unhashed fetches, no un-pinned `builtins.fetchTarball` anywhere.
- Never ship a manifest row whose packaging shape bypasses the safety-class
  scheme. The validator is the floor. Review is the ceiling.
- Vulnerabilities never enter a public issue. Never open a public issue that
  describes an exploitable bug. Report through the
  [GitHub security advisory](https://github.com/kailash-os/kailash-packages/security/advisories/new)
  link; see [`SECURITY.md`](SECURITY.md).
