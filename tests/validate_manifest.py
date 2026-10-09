#!/usr/bin/env python3
"""manifest-wellformed check (KA-04.1 strictness for categories.yaml).

Growth path: KA-02.2 (schema headers) hardens presence; KA-04.1 adds the
categories structural invariants below; KA-05.1 adds the tools.yaml
invariants (unique ids, categories exist, bespoke => derivation path,
ATTACK >= 1 ATLAS tactic, purge-resurrection guard).

Categories invariants (KA-04.1):
  - the file exists and parses as YAML
  - every entry carries: id, layer, kind, name, purpose, coverage, tools
  - layer is CLASSIC | ATTACK | DEFENCE | BUILD (CORE is the substrate)
  - kind is category | data-pack; data-pack entries are opt-in
  - ids are unique
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "..", "manifest")

LAYERS = {"CLASSIC", "ATTACK", "DEFENCE", "BUILD"}
KINDS = {"category", "data-pack"}
REQUIRED = ("id", "layer", "kind", "name", "purpose", "coverage", "tools")


def fail(msg: str) -> int:
    print("manifest-wellformed: FAIL:", msg)
    return 1


def main() -> int:
    try:
        import yaml
    except ImportError:
        print("pyyaml unavailable in check env")
        return 1

    cats_path = os.path.join(MANIFEST, "categories.yaml")
    if not os.path.exists(cats_path):
        return fail("categories.yaml missing (KA-04.1 owns it)")
    with open(cats_path) as f:
        doc = yaml.safe_load(f)

    entries = (doc or {}).get("categories")
    if not isinstance(entries, list):
        return fail("categories.yaml: top-level 'categories' list missing")
    if not entries:
        return fail("categories.yaml: no entries")

    seen = set()
    per_layer = {}
    for e in entries:
        if not isinstance(e, dict):
            return fail("entry is not a mapping: %r" % (e,))
        for k in REQUIRED:
            if k not in e or e[k] in (None, ""):
                return fail("entry %r missing required field: %s" % (e.get("id"), k))
        if e["layer"] not in LAYERS:
            return fail("%s: bad layer %r" % (e["id"], e["layer"]))
        if e["kind"] not in KINDS:
            return fail("%s: bad kind %r" % (e["id"], e["kind"]))
        if e["kind"] == "data-pack" and not e.get("opt_in"):
            return fail("%s: data-pack must be opt-in" % e["id"])
        if not isinstance(e["tools"], int) or isinstance(e["tools"], bool) or e["tools"] < 0:
            return fail("%s: tools must be a non-negative int" % e["id"])
        if e["id"] in seen:
            return fail("duplicate category id: %s" % e["id"])
        seen.add(e["id"])
        if e["kind"] == "category":
            per_layer[e["layer"]] = per_layer.get(e["layer"], 0) + e["tools"]

    # §3.6 post-purge reconcile: layer primary-slot totals count CATEGORIES
    # only — data-packs (c-07 sdr-tools +6; wordlists-mega at KA-07.2) are
    # excluded, which is what makes the four totals sum to ~337.
    LAYER_TOTALS = {"CLASSIC": 141, "ATTACK": 59, "DEFENCE": 46, "BUILD": 91}
    for layer, got in sorted(per_layer.items()):
        want = LAYER_TOTALS[layer]
        if got != want:
            return fail(
                "layer %s primary slots %d != census %d (§3.6; data-packs excluded)"
                % (layer, got, want)
            )

    print(
        "manifest-wellformed: OK (%d entries; primary slots: %s; data-packs excluded from counts)"
        % (
            len(entries),
            ", ".join("%s %d" % (l, n) for l, n in sorted(per_layer.items())) or "none",
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
