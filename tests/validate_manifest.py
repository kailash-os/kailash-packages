#!/usr/bin/env python3
"""manifest-wellformed check — presence-lenient stub state (#66 / KA-02.1).

KA-02.2 (#67) adds the schema headers and hardens this to strict;
KA-04/KA-05 fill the real content; the gate grows the full invariants
with them (unique ids, categories exist, bespoke => derivation path,
ATTACK >=1 ATLAS tactic, purge-resurrection guard).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "..", "manifest")

def main() -> int:
    tools = os.path.join(MANIFEST, "tools.yaml")
    cats = os.path.join(MANIFEST, "categories.yaml")
    missing = [p for p in (tools, cats) if not os.path.exists(p)]
    if missing:
        # lenient: stub state (#66) — the files land with KA-02.2
        print("manifest files not yet present (stub state):", *missing)
        return 0
    for p in (tools, cats):
        try:
            import yaml  # noqa: F401
        except ImportError:
            print("pyyaml unavailable; presence-only check")
            break
    print("manifest files present")
    return 0

if __name__ == "__main__":
    sys.exit(main())
