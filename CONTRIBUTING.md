# Contributing

Contributions are welcome. This document defines the working agreement: how
changes are proposed, reviewed, and merged, and what the continuous-integration
gates enforce.

## What this repo is

`kailash-packages` is the packaging overlay for the
[Kailash OS](https://github.com/kailash-os/kailash-os) distribution: the
manifests (`manifest/tools.yaml`, `manifest/categories.yaml`) drive the
category tree and tool entries; `pkgs/` holds the auto-called derivations;
`nvfetcher/` pins every upstream source. Changes here update the packaging
surface **separately** from the OS itself (the OS repo pins this flake as an
input).

## Ground rules

1. **Never commit to `master`.** All work happens on a branch, one change per
   branch, merged via pull request. Branch names follow
   `<type>/<short-description>` with kebab-case — e.g. `feat/attack-tools`,
   `fix/nvfetcher-pin`, `docs/category-map`.
2. **Conventional Commits.** Every commit message follows
   the [specification](https://www.conventionalcommits.org/en/v1.0.0):
   `type(scope): subject`.
   - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`.
   - `scope` is a surface: `manifest` (tools/categories), `pkgs`
     (derivations), `nvfetcher` (source pins), `flake`, `docs`, `ci`.
   - Subject: imperative, lowercase, no trailing period. Body (optional):
     what changed and why; wrap at 72 columns.
3. **Sign everything.** Commits must be GPG- or SSH-signed
   (`git config --global commit.gpgsign true`); releases are
   signed tags — unsigned commits and unsigned tags are
   not merged/published. Verify with `git log --show-signature` / `git tag -v`.
4. **One logical change per PR.** Small, reviewable diffs merge faster.
5. **Pre-commit runs locally.** Install the hooks once per clone —
   `pre-commit install && pre-commit install --hook-type pre-push` —
   then every `git commit` and `git push` runs the same hook set CI runs
   (bypass with `--no-verify` for the rare legitimate exception).

## Engineering standard: hypothesis-first TDD

Every feature, fix and refactor follows **hypothesis → failing test → minimal implementation → refactor** (see kailash-os/kailash-os#119 for the scope clauses and #51 for the standing spec):

1. State the hypothesis in the issue: expected behaviour, assumed mechanism, falsifying observation.
2. **Commit the failing test first** on the feature branch; run it and paste the RED run's failure line into the PR.
3. Implement the minimum that passes; then the suite; then refactor with tests green.
4. Edge/error paths (overflow, malformed input, failure modes) are covered before close.

For manifest work the test is the `manifest-wellformed` gate (and, from KA-05.1, the invariant suite) run against the changed file.

**Harness before capability.** The check that gates a behaviour ships in the same PR as the behaviour; nothing merges ahead of the check that would catch its regression. Where a new gate surface is introduced, the negative case (the gate fails on defective input) is proven in CI, not asserted in prose.

**GitHub Actions is the authoritative check and build surface.** The acceptance suite executes on hosted ubuntu runners (`nix flake check --all-systems`, derivation checks); contributor machines run the same suite for development only and never as merge evidence. Self-hosted runners are reserved for disk-bound image builds per the OS repo's KA-15 arrangement.

## Security-sensitive changes

Manifest and packaging changes are the security surface of the distribution
(see [SECURITY.md](SECURITY.md)):

- **Vulnerabilities are not issues.** Follow [SECURITY.md](SECURITY.md) — never
  open a public issue for an unreported vulnerability.
- **Offensive tooling entries** (`layer-attack`) must declare their safety
  level in the manifest; tools with active-exploit safety stay
  double-gated (host opt-in + shell opt-in) via the OS side. A manifest entry
  that new-tools such a tool without its gates is rejected in review.
- **Source pins are contract** — `nvfetcher` pins (with recorded hashes)
  change only with the manifest entry they belong to, in the same PR.
- **Taxonomy integrity:** category moves map to ATLAS/OWASP bindings; state
  the mapping impact in the PR body.

## CI on every pull request

| Check | What it does |
|---|---|
| `flake-check` | `nix flake check --all-systems` on hosted runners — everything evaluates for every declared system and the `manifest-wellformed` gate builds (full per-package matrix at KA-15) |
| Dependency Review | flags vulnerable or licence-incompatible dependency changes |
| OpenSSF Scorecard | publishes the security-posture score |

pre-commit hooks (whitespace, YAML/JSON validity, large-file guards,
`detect-private-key`, shellcheck) run locally on every commit.

## Commits and pull requests

- Push your branch and open a PR against `master`; describe the what and the why.
- Link the `KA-XX` issue the change implements; the project board is
  [kailash Roadmap](https://github.com/orgs/kailash-os/projects/1).
- Releases are signed tags (`git tag -s vX.Y.Z`).

## Reporting bugs

Open a [GitHub issue](https://github.com/kailash-os/kailash-packages/issues/new)
with the flake revision, the manifest surface you hit, and the error excerpt.
Security issues never go here — [SECURITY.md](SECURITY.md) instead.

## Licence

The project is licensed under **BSD-3-Clause** — see [LICENSE](LICENSE).
Contributions are made under **BSD-3-Clause**: by submitting a pull request you
agree your work is licensed under the project's BSD-3-Clause terms.
