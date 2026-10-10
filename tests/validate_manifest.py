#!/usr/bin/env python3
"""manifest-wellformed check (KA-04.1 strictness + KA-04.2/KA-04.4 censuses).

Growth path: KA-02.2 (schema headers) hardens presence; KA-04.1 adds the
categories structural invariants below; KA-04.2 adds the ATTACK census
invariants (ATLAS + OWASP LLM:2026 presence per ATTACK category);
KA-04.4 adds the OPS census invariants (set existence for O-1…O-7,
layers renamed BUILD→OPS per the naming umbrella os#121 + mirror #9,
OPS=91 enforced exactly when present, per-layer reconcile permissive
to layers whose rows have not landed) and the in-file exclusions
ledger (plan §3.7, the no-resurrection guard, as a header comment
block in categories.yaml); KA-05.1 adds the tools.yaml
invariants (unique ids, categories exist, bespoke => derivation path,
purge-resurrection guard).

Categories invariants (KA-04.1):
  - the file exists and parses as YAML
  - every entry carries: id, layer, kind, name, purpose, coverage, tools
  - layer is CLASSIC | ATTACK | DEFENCE | OPS (CORE is the substrate;
    layer named OPS per the BUILD→OPS rename, os#121)
  - kind is category | data-pack; data-pack entries are opt-in
  - ids are unique

OPS census invariants (KA-04.4):
  - the deliberate-exclusions ledger (plan §3.7) is recorded in-file
    in the categories.yaml header, naming every excluded class
  - every OPS category entry matches the O-1…O-7 census set

ATTACK census invariants (KA-04.2):
  - every ATTACK entry carries a non-empty atlas_tactics list of real
    MITRE ATLAS tactic ids (AML.TA0000…AML.TA0015, 2026.05 matrix)
  - every ATTACK category entry carries a non-empty owasp_llm field
    ({2026: [...], v2: [...]} or a map of epoch -> LLM classes)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "..", "manifest")

LAYERS = {"CLASSIC", "ATTACK", "DEFENCE", "OPS"}
KINDS = {"category", "data-pack"}
REQUIRED = ("id", "layer", "kind", "name", "purpose", "coverage", "tools")

# §3.6 ATTACK census — the category set A-04.2 owns. The census-existence
# invariant fails the gate while the ATTACK layer is still missing from
# categories.yaml (KA-04.2's RED), independent of per-entry checks.
ATTACK_CENSUS_IDS = {
    "a-01-ai-recon",
    "a-02-prompt-injection-jailbreaks",
    "a-03-agentic-mcp-tool-use",
    "a-04-model-supply-chain",
    "a-05-model-extraction-inversion",
    "a-06-multimodal-physical-ai",
    "a-07-ai-system-exploitation",
    "a-08-data-poisoning",
}

# MITRE ATLAS tactic ids — 2026.05 matrix (16 tactics, AML.TA0000…TA0015;
# verified against mitre-atlas/atlas-data dist/v6/ATLAS-2026.05.yaml).
ATLAS_TACTICS = {
    "AML.TA%04d" % i for i in range(16)
}
ATLAS_TACTIC_BY_ID = {k: True for k in ATLAS_TACTICS}

# §3.6 OPS census — the category set KA-04.4 owns. The census-existence
# invariant fails the gate while the OPS layer is still missing from
# categories.yaml (KA-04.4's RED), independent of per-entry checks.
OPS_CENSUS_IDS = {
    "o-01-mlops-ml-engineering",
    "o-02-compute-serving-infrastructure",
    "o-03-vector-stores-retrieval",
    "o-04-local-llm-inference-labs",
    "o-05-ai-engineering-sdks-dev-env",
    "o-06-documentation-reporting-authoring",
    "o-07-agent-mcp-operability",
}

# KA-04.4 exclusions-ledger invariant: the deliberate-exclusions block
# (plan §3.7 — the no-resurrection guard, mirrored by the KA-05.1
# purge-resurrection guard upstream) must be present in the
# categories.yaml header (schema-stable comment) and must name every
# excluded class, each with its §3.7 line reference.
LEDGER_MARKER = "DELIBERATE EXCLUSIONS LEDGER"
LEDGER_CLASSES = (
    "hardware & rf & wifi/bluetooth tooling",
    "paid-licence tools",
    "cloud-only saas",
    "unmaintained tools",
    "network-infrastructure arsenal",
)


def fail(msg: str) -> int:
    print("manifest-wellformed: FAIL:", msg)
    return 1


def check_attack_census(e: dict) -> str:
    """KA-04.2: ATLAS tactic + OWASP LLM presence for ATTACK entries.

    Returns a failure message or "" when the entry satisfies the census
    invariants. Data-packs: ATLAS required (the mapping is the point of
    the census); OWASP LLM classes required on categories only (v2.4
    records epoch classes per tool, and the category table is the
    per-layer census view).
    """
    if e["layer"] != "ATTACK":
        return ""
    at = e.get("atlas_tactics")
    if not isinstance(at, list) or not at:
        return "%s: ATTACK entry missing atlas_tactics (KA-04.2 census gap)" % e["id"]
    for t in at:
        if t not in ATLAS_TACTIC_BY_ID:
            return (
                "%s: unknown MITRE ATLAS tactic %r (must be AML.TA0000…TA0015, "
                "2026.05 matrix)" % (e["id"], t)
            )
    if e["kind"] == "category":
        ol = e.get("owasp_llm")
        if not isinstance(ol, dict) or not ol:
            return "%s: ATTACK category missing owasp_llm (KA-04.2 census gap)" % e["id"]
        if "2026" not in ol:
            return (
                "%s: owasp_llm missing the 2026 epoch (KA-04.2 records both "
                "epochs: 2026 + v2)" % e["id"]
            )
    return ""


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
        census_fail = check_attack_census(e)
        if census_fail:
            return fail(census_fail)
        if e["kind"] == "category":
            per_layer[e["layer"]] = per_layer.get(e["layer"], 0) + e["tools"]

    # KA-04.2 census-existence: the ATTACK layer's 8-category set must be
    # present (and only it) — fails while categories.yaml still carries
    # no ATTACK rows at all, where no per-entry check can fire.
    attack_ids = {
        e["id"] for e in entries if isinstance(e, dict) and e.get("layer") == "ATTACK"
    }
    missing_census = ATTACK_CENSUS_IDS - attack_ids
    if missing_census:
        return fail(
            "ATTACK census incomplete (KA-04.2): missing %s"
            % ", ".join(sorted(missing_census))
        )
    extra_census = attack_ids - ATTACK_CENSUS_IDS
    if extra_census:
        return fail(
            "ATTACK census unexpected entries (KA-04.2): %s"
            % ", ".join(sorted(extra_census))
        )

    # KA-04.4 census-existence: the OPS layer's 7-category set must be
    # present (and only it) — fails while categories.yaml still carries
    # no OPS rows at all, where no per-entry check can fire.
    ops_ids = {
        e["id"] for e in entries if isinstance(e, dict) and e.get("layer") == "OPS"
    }
    missing_ops = OPS_CENSUS_IDS - ops_ids
    if missing_ops:
        return fail(
            "OPS census incomplete (KA-04.4): missing %s"
            % ", ".join(sorted(missing_ops))
        )
    extra_ops = ops_ids - OPS_CENSUS_IDS
    if extra_ops:
        return fail(
            "OPS census unexpected entries (KA-04.4): %s"
            % ", ".join(sorted(extra_ops))
        )

    # KA-04.4 exclusions ledger: the header must carry the in-file
    # ledger block (plan §3.7, the no-resurrection guard) and name
    # every excluded class.
    with open(cats_path) as f:
        cats_text = f.read().lower()
    if LEDGER_MARKER.lower() not in cats_text:
        return fail(
            "exclusions ledger (plan §3.7, KA-04.4) missing from "
            "categories.yaml header"
        )
    for cls in LEDGER_CLASSES:
        if cls not in cats_text:
            return fail(
                "exclusions ledger missing class %r (KA-04.4)" % cls
            )

    # §3.6 post-purge reconcile: layer primary-slot totals count CATEGORIES
    # only — data-packs (c-07 sdr-tools +6; wordlists-mega at KA-07.2) are
    # excluded, which is what makes the four totals sum to ~337. The
    # reconcile stays permissive to layers whose rows have not landed yet
    # (DEFENCE at KA-04.3) and enforces the landed layers exactly: the
    # BUILD→OPS rename keeps OPS at 91 (os#121 naming umbrella).
    LAYER_TOTALS = {"CLASSIC": 141, "ATTACK": 59, "DEFENCE": 46, "OPS": 91}
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
