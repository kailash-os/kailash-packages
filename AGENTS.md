# kailash-packages: guide for contributors and coding agents

This file is the single source of truth for humans and coding agents
(GitHub Copilot, Claude, Cursor, Hermes, etc.) working on kailash-packages.
Tool-specific files (`CLAUDE.md`, `.github/copilot-instructions.md`) only
point here. When this file and a tool-specific file disagree, this file wins.

Read the [Manifest and taxonomy](#the-manifest-and-the-taxonomy-single-home-rule),
[Testing](#testing) and [Security](#security) sections before changing
anything. The rest is a map of the repository.

## Project overview

`kailash-packages` is the overlay of the
[Kailash OS](https://github.com/kailash-os/kailash-os) distribution: a
flake-parts Nix overlay carrying pinned upstream sources, package derivations
and the **manifest** — the taxonomy's single home. The OS root flake pins this
repo; profiles in the OS repo compose categories whose entries are defined
here.

The roadmap board ([org project 1](https://github.com/orgs/kailash-os/projects/1))
carries issue `KA-NN` items;
[issue #61](https://github.com/kailash-os/kailash-os/issues/61) on the OS repo
is the canon map — the dependency graph plus the sprint decomposition register
every new roadmap item adds a row to.

## Repository structure

| Directory | Purpose |
| --- | --- |
| `flake.nix` + `flake-parts/` | The overlay flake: packages, checks, and the export consumed by the OS root flake's `kailash-packages` input |
| `manifest/` | `categories.yaml` (31-category census across CORE + CLASSIC/ATTACK/DEFENCE/OPS) and `tools.yaml` (tool inventory: ids, licences, packaging shapes, safety classes, ATLAS + standards mappings) |
| `nvfetcher/` | Upstream source pins: `config.toml` + committed `_sources/` — regeneration is nvfetcher, never hand edits to `_sources` |
| `pkgs/` | Package derivations, auto-called; bespoke (overlay-defined) tools carry a derivation path recorded in the manifest |
| `tests/` | The manifest validator (`tests/validate_manifest.py`) — the single enforcement point for manifest invariants |

## The manifest and the taxonomy (single home rule)

The taxonomy is **versioned data**, not prose: every later artifact (modules,
profiles, menu, CLI, docs, site) generates from these two files. One-tool-
one-primary-category with secondary tags is validator-enforced; layer/category/
tool facts are written here, never duplicated into the OS modules, READMEs or
site copy.

The census is the spec's §3.6 post-purge table: CLASSIC (~141 tool slots),
ATTACK (~59), DEFENCE (~46), OPS (~91), plus the C-7 SDR pack recorded as
`opt-in: data-pack` — never on default profiles or images. Deliberate
exclusions (§3.7: no hardware/RF/wifi tools, no paid-licence tools, no
unmaintained or cloud-only tools) are the "no-resurrection guard": the
manifest validator refuses purged tooling — do not reintroduce it.

Data-accuracy rules:

- ATLAS tactic mappings (ATTACK layer) and ASVS/AISVS/MLSVS/OWASP-LLM mappings
  (DEFENCE layer) are manifest fields with real identifiers — verify mappings
  against the public MITRE ATLAS dataset before writing one; never invent a
  technique id.
- Licences are recorded per tool in the manifest; unfree posture is explicit
  at the flake level and never widened for convenience.
- Safety classes are per-tool manifest fields (`safety:exp` tooling wires the
  lab-mode gate in the OS repo) — a manifest row without its safety class is
  validator-blocking.

## Testing

The repo follows the
[hypothesis-first TDD standard](https://github.com/kailash-os/kailash-os/issues/51):
**spec (from the issue's plan reference) → RED (watched, committed) → GREEN →
PR**. The engineering standard pairs it with
[harness-before-capability ordering](https://github.com/kailash-os/kailash-os/issues/119):
the check that gates a behaviour ships in the same PR as the behaviour, and a
new gate's negative case is proven in CI, not asserted.

- **Manifest invariants live in the validator** (`tests/validate_manifest.py`):
  schema shape, unique ids, categories-exist, derivation-path presence for
  bespoke tools, ATLAS coverage on ATTACK tools, the no-resurrection guard.
  A new invariant extends the validator (RED first), never an ad-hoc script.
- **Run what CI runs**: `nix flake check` plus the validator, before opening
  a PR. The `flake-check` workflow is the authoritative gate; local green is
  development evidence only.
- **No invented transcripts.** Any claim about a build or validation run cites
  its real output, plus the issue/PR where it was recorded; without a run,
  mark it PENDING with the owning issue — never approximate.

## Signing

**Everything is GPG-signed, always.** Commits AND tags
(`git config commit.gpgsign true`; signing key `AAF8226F3F4C1712` —
authored and committed as `Shain.Singh@owasp.org`). PR CI enforces
`required_signatures`; an unsigned or badly-attributed commit blocks the PR.
Never use the f5-attributed key for kailash work — the signing key and the
commit email must agree with the GitHub-verified identity or verification
fails with `bad_email` and the PR cannot merge.

## Pull requests

Follow [`CONTRIBUTING.md`](CONTRIBUTING.md); leaf branch cut from **current
`origin/main`**, one logical change per PR, watched RED before GREEN, all
commits GPG-signed. Title carries the task id (`KA-XXn — summary [child of
KA-XX]`); the body links the child issue (`Closes #NN`) and notes the parent
gate stays open, and states **what** changed, **why**, and **how verified**.

## Labels

| Label | Meaning |
| --- | --- |
| `KA-XXn — <summary>` (in the TITLE, not a label) | issue/PR identity |
| `area:manifest|packaging|nix|layer-classic|layer-attack|layer-defence|layer-ops|testing|repo|docs|github` | component (the current catalog) |
| `type:task` | a leaf-sized roadmap slice (RED→GREEN→merge) — the only `type:*` label in the catalog today |
| `target:v0.1|v0.2|backlog` | milestone |
| `s:xs|s:s|s:m|s:l` | sprint effort |

Board status is an org-project **field**, not a label. Cross-repo children
never auto-close: a PR merged in this repo does not close an issue filed on
`kailash-os` — close it there with a "merged via <repo>#N" comment after
verifying the merge. Growing the label catalog is a deliberate catalog change,
not agent improvisation.

## Security

This overlay pins the supply chain of a distribution that packages offensive
tooling — the attack surface is the **manifest itself**:

- A tool's source URL, pin and licence are attacker-relevant data; validate
  changes to them in review (new `nvfetcher` names, changed pins, licence
  downgrades).
- Inputs stay pinned: committed `_sources/`, no floating refs, no unhashed
  fetches, no un-pinned `builtins.fetchTarball` anywhere.
- Never ship a manifest row whose packaging shape bypasses the safety-class
  scheme; the validator is the floor, review is the ceiling.
- Vulnerabilities: never open a public issue describing an exploitable bug —
  report through the
  [GitHub security advisory](https://github.com/kailash-os/kailash-packages/security/advisories/new)
  link; see [`SECURITY.md`](SECURITY.md).
