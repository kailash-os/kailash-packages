#!/usr/bin/env python3
# tools/gen-exp-wrap.py — exp-wrap wrapper-input generator (KA-19.1, kailash-os#94).
#
# Parses manifest/tools.yaml, selects the rows whose `safety.level` is
# `exp`, and emits the wrapper-generation inputs to stdout as one JSON
# blob:
#
#   {"exp_ids":   ["<tool-id>", ...],
#    "wrappers":  [{"id": ..., "program": ..., "derivation": <path|null>},
#                  ...]}
#
# Deterministic: rows sorted by id, sort_keys on. The packages repo owns
# the manifest + this emit surface; the WRAPPER GENERATION (the lab-mode
# gate) lives in the OS repo's modules/base/safety-defaults.nix — the
# gateFor hook point KA-19.1 wires (kailash.safety.extraTools).
#
# `program` resolution mirrors the OS gate's mainProgOf convention
# (nixos_menu.exec when the row carries one, else the row name, else the
# row id); `derivation` is the packaging.derivation path or null.
#
# RED STUB (KA-19.1): this commit carries the check + the self-test
# contract and a deliberately empty generator; the watched RED on the
# exp-wrap-manifest-emit / exp-wrap-generator-self-test checks is the
# test-first evidence. The real generator lands in the GREEN commit.

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MANIFEST = os.path.join(HERE, os.pardir, "manifest", "tools.yaml")


def emit_inputs(tools):
    """RED stub core: emits an empty surface (self-test below pins the
    real contract: exp selection, non-exp exclusion, id shapes, empty
    manifest)."""
    return {"exp_ids": [], "wrappers": []}


def load_tools(path):
    """Parse the manifest with PyYAML (guaranteed in both repos' check
    envs — the flake legs build python3.withPackages ps.pyyaml)."""
    import yaml  # type: ignore[import-not-found]

    with open(path, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh.read())
    if doc is None:
        return []
    tools = doc.get("tools") or [] if isinstance(doc, dict) else doc
    return [t for t in tools if isinstance(t, dict)]


def generate(path):
    return emit_inputs(load_tools(path))


def self_test() -> int:
    """Assert-based core self-check (no nix, no network). RED: the stub
    core fails every exp-selection case."""
    cases = [
        (
            {"schema_version": 1, "tools": []},
            {"exp_ids": [], "wrappers": []},
        ),
        (
            {
                "tools": [
                    {"id": "garak", "safety": {"level": "exp"}},
                    {"id": "nmap", "safety": {"level": "safe"}},
                    {"id": "sqlmap", "safety": {"level": "requires-target"}},
                ]
            },
            {
                "exp_ids": ["garak"],
                "wrappers": [{"id": "garak", "program": "garak", "derivation": None}],
            },
        ),
    ]
    for i, (doc, want) in enumerate(cases):
        got = emit_inputs(doc.get("tools") or [])
        expect = want["exp_ids"]
        assert got["exp_ids"] == expect, f"case {i}: exp_ids {got['exp_ids']!r} != {expect!r}"
        assert got["wrappers"] == want["wrappers"], f"case {i}: wrappers {got['wrappers']!r} != {want['wrappers']!r}"
    # id shapes: every exp id is a manifest slug
    for tid in emit_inputs(cases[1][0]["tools"])["exp_ids"]:
        assert tid and all(c.isalnum() or c in "._-" for c in tid), f"bad id shape: {tid!r}"
    print("tools/gen-exp-wrap.py: self-test OK")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    path = None
    i = 0
    while i < len(argv):
        if argv[i] == "--manifest-file":
            i += 1
            path = argv[i]
        i += 1
    out = generate(path or DEFAULT_MANIFEST)
    sys.stdout.write(json.dumps(out, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
