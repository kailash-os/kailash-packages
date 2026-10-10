#!/usr/bin/env python3
"""tools/emit-matrix.py — packages-local build-matrix adapter (KA-05.2).

The vendored tools/manifest-matrix.py (KA-15.1, byte-identical mirror
pair with kailash-os) predates the §5.2 filled-table shape: its pure
core maps list-of-str tool ids, and its stdlib YAML fallback covers
only the header-only manifest. When the census lands dict rows
(KA-05.x), this adapter emits the same matrix JSON from the REAL
state, following the generator's own documented rule — "during the
census fill (KA-05) the matrix follows the real pkgs/ build surface
instead of emitting an empty matrix that silently skips CI":

  * header-only tools table  -> passthrough to the vendored generator's
    repo-mode (the pkgs/ auto-call fallback, unchanged behaviour);
  * filled table             -> ids parsed per §5.2 (dict rows), filtered
    to pkgs/<id>/default.nix dirs that EXIST on this rev — native/stale
    rows resolve through nixpkgs (nothing to build here), module/data
    rows ship no derivation, and bespoke rows land with KA-07.x, so the
    build surface grows as derivations land.

The generator file itself stays byte-identical with the OS mirror (the
workflow's cmp step enforces it); this adapter is packages-local by
design. Self-test: python3 tools/emit-matrix.py --self-test.
"""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SYSTEMS = ("x86_64-linux", "aarch64-linux")


def _load_manifest(manifest_dir):
    import yaml  # the workflow installs pyyaml before calling this

    with open(os.path.join(manifest_dir, "tools.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh.read()) or {}


def _pkgs_build_surface(repo_dir):
    """pkgs/ auto-call dirs (sorted): the real build surface — the same
    filter pkgs/auto-call.nix applies (default.nix present, no .nocall)."""
    pkgs_dir = os.path.join(repo_dir, "pkgs")
    if not os.path.isdir(pkgs_dir):
        return []
    names = []
    for name in sorted(os.listdir(pkgs_dir)):
        tool_dir = os.path.join(pkgs_dir, name)
        if (
            os.path.isdir(tool_dir)
            and os.path.isfile(os.path.join(tool_dir, "default.nix"))
            and not os.path.isfile(os.path.join(tool_dir, ".nocall"))
        ):
            names.append(name)
    return names


def matrix_from_state(manifest_dir, repo_dir):
    """Filled-or-stub manifest state -> GitHub Actions matrix dict.

    Deterministic: sorted ids, fixed SYSTEMS order, no invented legs.
    """
    manifest = _load_manifest(manifest_dir)
    tools = manifest.get("tools") or []
    pkgs_names = _pkgs_build_surface(repo_dir)
    pk = set(pkgs_names)

    if tools:
        ids = [t["id"] for t in tools
               if isinstance(t, dict) and t.get("id")]
        ids = sorted(i for i in ids if i in pk)
    else:
        # header-only stub: the vendored generator's documented fallback —
        # the pkgs/ surface without any manifest row requirement
        ids = sorted(pkgs_names)
    return {
        "include": [
            {"package": name, "system": system}
            for name in ids
            for system in SYSTEMS
        ]
    }


def main(argv):
    if "--self-test" in argv:
        import tempfile as tempfile_mod

        with tempfile_mod.TemporaryDirectory() as td:
            mf = os.path.join(td, "manifest")
            os.makedirs(mf)
            pk = os.path.join(td, "pkgs")
            for name in ("subfinder", "dnsrecon", "skipped-nocall",
                         "skipped-nodrv"):
                d = os.path.join(pk, name)
                os.makedirs(d)
                if name != "skipped-nodrv":
                    with open(os.path.join(d, "default.nix"), "w") as fh:
                        fh.write("{}\n")
            with open(os.path.join(pk, "skipped-nocall", ".nocall"), "w") as fh:
                fh.write("\n")

            # stub state: matrix follows the pkgs/ surface
            with open(os.path.join(mf, "tools.yaml"), "w") as fh:
                fh.write("schema_version: 1\ntools: []\n")
            got = matrix_from_state(mf, td)
            assert got == {"include": [
                {"package": "dnsrecon", "system": s}
                for s in SYSTEMS
            ] + [
                {"package": "subfinder", "system": s}
                for s in SYSTEMS
            ]}, "stub state must fall back to the pkgs/ surface, got %r" % got

            # filled state: pkgs-existence filter drops native rows and
            # bespoke rows whose derivations have not landed yet
            with open(os.path.join(mf, "tools.yaml"), "w") as fh:
                fh.write(
                    "tools:\n"
                    "  - {id: nmap, packaging: {status: native}}\n"
                    "  - {id: subfinder, packaging: {status: bespoke}}\n"
                    "  - {id: webshell-analysis-pack, packaging: {status: data}}\n"
                    "  - {id: gvm, packaging: {status: module}}\n"
                )
            got = matrix_from_state(mf, td)
            assert got == {"include": [
                {"package": "subfinder", "system": s} for s in SYSTEMS
            ]}, "filled state must filter to the real pkgs/ surface, got %r" % got
        print("emit-matrix self-test: OK")
        return 0

    manifest_dir = os.path.join(ROOT, "manifest")
    if "--manifest-dir" in argv:
        manifest_dir = argv[argv.index("--manifest-dir") + 1]
    json.dump(matrix_from_state(manifest_dir, os.path.dirname(manifest_dir)),
              sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
