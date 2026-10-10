# kailash — the manifest-aware CLI core (KA-14.1, plan §7.1–7.4).

The manifest-aware front-end (plan §7.1): Python, packaged in the packages
repo, driven by the same two manifest files — **not a second source of
truth**. This directory carries the loader + command core; the wheel
metadata is `pyproject.toml` (the packaged artifact lands with KA-14.2 via
`pkgs/kailash`).

Layout (installed / flake source / repo all resolve the same way — the
package dir sits beside a sibling `manifest/` two levels up):

```
cli/
├── pyproject.toml          # wheel name/version/entry: kailash → kailash.cli:main
├── check-kailash-cli.py    # checks.kailash-cli-self-test exercise (data-driven assertions)
└── kailash/
    ├── __init__.py
    ├── manifest.py         # loader: load_categories()/load_tools() + paths
    └── cli.py              # argparse: list/search/info (+ manifest check)
```

## Loader resolution (`manifest.py`)

Paths resolve relative to the package module (`cli/kailash/__file__` →
`../../manifest/…`), which holds in the repo tree, in the flake source
tree (`src = self`), and installed — the wheel ships the whole `cli/`
subtree. `KAILASH_MANIFEST` (the §7.3 env spelling; §7.3's store-baked
wiring lands with KA-14.2's wrapProgram) overrides both files' directory.
pyyaml is declared the same way the validator check declares it —
`python3.withPackages (ps: [ ps.pyyaml ])` in the check env, the same
dependency in the wheel metadata.

Data accessors only: the §5.2 manifest invariants stay single-homed in
`tests/validate_manifest.py` (AGENTS.md single-home rule) — this package
never re-implements them.

## Command surface (§7.2 slice)

- `kailash list [--layer L] [--category C] [--status S] [--json]` — tools
  rows once the census table fills (status filters on
  `packaging.status`); the category tree (id · layer · kind · primary
  tool slots) while the header-only tools stub stands. `--layer`
  validates against the layers categories.yaml actually defines.
- `kailash search <query> [--json]` — case-insensitive over id, name,
  description, tags.
- `kailash info <tool-id> [--json]` — the manifest record as JSON; an
  absent id exits 1 (with the header-only stub, every id is absent).
- `kailash manifest check` — loader self-inventory as JSON (test aid for
  data-driven assertions; `manifest validate` runs the repo validator at
  KA-14.2).

Exit codes: **0** ok · **1** no results · **2** usage error or
unreadable/unparsable manifest (argparse exits 2 on its own). `--json`
emits a stable JSON shape per §7.4 and is accepted before or after the
subcommand.

## Verification

`cli/check-kailash-cli.py` is the flake-check exercise
(`checks.kailash-cli-self-test`): it runs the commands in-process and
asserts the printed rows against an independent pyyaml parse of the
manifest DATA — never hardcoded row counts — so the check stays green as
manifest rows land (KA-05.x). The watched negative case (`info` on an
absent id exits 1) is proven by construction on every run.
