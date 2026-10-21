# kailash — the manifest-aware CLI core (KA-14.1, spec §6.1–7.4).

The CLI is the manifest-aware front-end (spec §6.1). Python implements it,
and the packages repo packages it. The same two manifest files drive it.
The CLI is **not a second source of truth**. This directory carries the
loader and the command core. The wheel metadata sits in `pyproject.toml`.
KA-14.2 ships the packaged wheel at `pkgs/kailash`.

Layout (installed / flake source / repo all resolve the same way — the
package dir sits beside a sibling `manifest/` two levels up):

```
cli/
├── pyproject.toml          # wheel name/version/entries: kailash, kailash-mcp (KA-25)
├── check-kailash-cli.py    # checks.kailash-cli-self-test exercise (data-driven assertions)
└── kailash/
    ├── __init__.py
    ├── manifest.py         # loader: load_categories()/load_tools()/load_profiles() + paths
    ├── cli.py              # argparse: list, search, info, profile list, manifest check, manifest validate
    └── mcp_server.py       # the MCP face (KA-25): the kailash-mcp entry point
```

## Loader resolution (`manifest.py`)

Paths resolve relative to the package module (`cli/kailash/__file__` →
`../../manifest/…`). The layout holds in the repo tree, in the flake source
tree (`src = self`), and installed — the wheel ships the whole `cli/`
subtree. The per-file env contract names files, not directories.
[spec §6.3](https://github.com/kailash-os/kailash-os/blob/master/docs/spec.md#63-the-manifest-baked-path-the-drift-killer)
carries the baked-path spelling. `KAILASH_MANIFEST` overrides the
`tools.yaml` file, `KAILASH_CATEGORIES` the `categories.yaml` file, and
`KAILASH_PROFILES` the `profiles.json` file. KA-14.2 bakes the packaged
binary's paths (the wrapProgram step). pyyaml is declared the same way the
validator check declares it — `python3.withPackages (ps: [ ps.pyyaml ])` in
the check env, and the same dependency in the wheel metadata.

Data accessors only: the
[spec §4.2](https://github.com/kailash-os/kailash-os/blob/master/docs/spec.md#42-the-tool-manifest-the-single-source-of-truth)
manifest invariants stay single-homed in `tests/validate_manifest.py`
(AGENTS.md single-home rule) — this package never re-implements them.

## Command surface (spec §6.2 slice)

- `kailash list [--layer L] [--category C] [--status S] [--json]` — one row
  per manifest tool: id, layer, category, `packaging.status`. The
  `--layer` flag validates against the layers `categories.yaml` carries.
  The `--status` flag reads the `packaging.status` value. The category tree
  shows only while the tools table is empty.
- `kailash search <query> [--json]` — one row per hit: id, name,
  description. The match is case-insensitive over id, name, description,
  tags, and the secondary category ids.
- `kailash info <tool-id> [--json]` — the manifest record as JSON. An
  absent id exits 1 with a message naming the id.
- `kailash manifest check` — the loader self-inventory as JSON. It is the
  data-driven assertion aid for the check exercise.
- `kailash manifest validate` — runs the repo manifest gate
  (`tests/validate_manifest.py`) in-process, against the manifest the CLI
  itself resolves. The per-file env overrides
  ([spec §6.3](https://github.com/kailash-os/kailash-os/blob/master/docs/spec.md#63-the-manifest-baked-path-the-drift-killer))
  name the files, so a baked store path validates the baked bytes. Exit 0
  carries the validator's OK line on a well-formed manifest. Exit 1 carries
  the FAIL line on a gate failure. Exit 2 means `tests/` is not beside the
  package (installed wheels carry `cli/` only). This is the KA-14.3 clause
  ([kailash-os#137](https://github.com/kailash-os/kailash-os/issues/137)):
  `kailash manifest validate` runs the CI gate locally.
- `kailash profile list [--json]` — one row per OS profile:
  `<name>\t<layers-summary>\t<description>`, read from the `profiles.json`
  file ([kailash-os#115](https://github.com/kailash-os/kailash-os/issues/115),
  the per-file env contract). The `KAILASH_PROFILES` env var names the
  file. The OS-side generator gives the file, and the packaged binary's
  wrapProgram bake points at it. Unset, the CLI reads the committed sample
  beside the package (`profiles/profiles.json`). With no file anywhere, the
  command exits 1 with a message naming `KAILASH_PROFILES`. More profile
  verbs (enable/…) land with the profile-apply items.

Exit codes: **0** ok · **1** no results · **2** a usage error or an
unreadable/unparsable manifest (argparse exits 2 on its own). `--json`
writes a stable JSON shape per spec §6.4 and works before or after the
subcommand.

## Verification

The flake-check exercise is `cli/check-kailash-cli.py`
(`checks.kailash-cli-self-test`). The exercise runs the commands in-process
and asserts the printed rows against an independent pyyaml parse of the
manifest data. It hardcodes no row counts, so the check stays green as
manifest rows land (KA-05.x). The exercise also carries the `manifest
validate` check pair: the validator's OK line, and the broken-fixture
FAIL line. The broken fixture reaches the CLI through the per-file env
contract. The watched negative case (`info`
on an absent id exits 1) is proven by construction on every run.
