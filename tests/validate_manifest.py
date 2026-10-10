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
block in categories.yaml); KA-05.1 adds the tools.yaml invariants
(§5.2 vocabulary: unique tool ids, unknown category ids rejected in
category and secondary_categories, bespoke => derivation path,
ATLAS tactics with the AML.T#### shape guard, §3.7
purge-resurrection guard, safety.level vocabulary).
The tools.yaml invariant suite is tests/test_invariants.py (fixture
  RED/GREEN evidence; kailash-os#74); the blocklist data constant is
  tests/invariants.py.

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

tools.yaml invariants (KA-05.1):
  - ids are unique
  - every tool category and secondary_categories value exists among
    categories.yaml ids
  - packaging.status bespoke carries a packaging.derivation path
  - every ATTACK-layer tool carries >= 1 atlas_tactics entry shaped
    AML.T#### (shape-level regex guard — dataset-lookup verification
    stays the census lanes' review job)
  - §3.7 no-resurrection: purged tool ids/names are a data-driven
    blocklist (tests/invariants.py)
  - safety.level is safe | requires-target | exp
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
# KA-05.1: shape-level guard for per-tool ATLAS technique ids. Only the
# SHAPE is validated here (AML.T + exactly four digits — the pattern
# every id in the public mitre-atlas dataset matches); the dataset
# lookup is not. Per AGENTS.md, mapping accuracy is verified against
# the public MITRE ATLAS dataset by the census lanes' review, never
# invented in data; a malformed id such as AML.T51 or TA0051 is
# validator-blocking even though it is a data defect, not a lookup one.
ATLAS_TOOL_PATTERN_RE = r"^AML\.T\d{4}$"
import re as _re  # noqa: E402  (kept beside the constant it names)

ATLAS_TOOL_PATTERN = _re.compile(ATLAS_TOOL_PATTERN_RE)

# KA-05.1: the safety.level vocabulary (§5.2). KA-19's exp-gating
# wiring in the OS repo is out of scope here — the manifest row
# records the class; the OS side wires the gate.
SAFETY_LEVELS = {"safe", "requires-target", "exp"}


def run_tools_checks(doc: dict, require_nonempty: bool = False, cat_ids=None) -> list:
    """tools.yaml invariants (KA-05.1, plan §5.2 vocabulary).

    Evaluates the invariant set over a parsed manifest document that
    carries a 'tools' list; every category id referenced by a tool
    (primary or secondary) must exist in the document's
    'categories' list, or in the explicit `cat_ids` set main() passes
    from the categories.yaml half it validated first (tools.yaml
    itself carries no category table). Each invariant violation
    becomes exactly ONE manifest-wellformed failure line, returned as
    a list of strings in first-violation order:

      - unique tool ids ("duplicate tool id")
      - categories-exist ("unknown category id '<id>'") for the
        primary category and every secondary_categories value;
        secondary_categories is optional but must be a list of str
        ("secondary_categories must be a list of strings") and never
        repeat the primary ("single primary category:")
      - packaging.status 'bespoke' carries a non-empty
        packaging.derivation path ("bespoke tool without
        packaging.derivation")
      - ATTACK-layer tools carry >= 1 atlas_tactics entry shaped
        AML.T#### ("ATTACK-layer tool without atlas_tactics" /
        "bad MITRE ATLAS technique id shape")
      - no-resurrection: tool id or name on the §3.7 blocklist
        (tests/invariants.py) is refused ("purged tooling (§3.7
        hardware/RF class)" / "purged tooling (§3.7 paid licence)")
      - safety.level in {safe, requires-target, exp}
        ("invalid safety.level")

    `require_nonempty` flips the KA-02.2 handover constraint (the gate
    accepts the empty tools list only until the census lanes seed
    rows); tools rows are not counted here — §3.6 primary-slot layer
    totals count category rows and are checked in main().
    """
    from invariants import BLOCK_PAID, NO_RESURRECTION  # §3.7 blocklist

    findings: list = []
    tools = doc.get("tools")
    if not isinstance(tools, list):
        findings.append(
            "manifest-wellformed: FAIL: tools.yaml: top-level 'tools' list missing"
        )
        return findings
    if not tools and require_nonempty:
        findings.append(
            "manifest-wellformed: FAIL: tools.yaml: no entries (KA-05 seeds rows)"
        )
        return findings

    if cat_ids is None:
        cat_ids = {
            e.get("id") for e in (doc.get("categories") or []) if isinstance(e, dict)
        }

    seen_tools = set()
    for t in tools:
        if not isinstance(t, dict):
            findings.append(
                "manifest-wellformed: FAIL: tool entry is not a mapping: %r" % (t,)
            )
            return findings
        tid = t.get("id")

        # ids are unique
        if not tid or not isinstance(tid, str):
            findings.append("manifest-wellformed: FAIL: tool entry missing id")
            return findings
        if tid in seen_tools:
            findings.append(
                "manifest-wellformed: FAIL: duplicate tool id: %s" % tid
            )
            return findings
        seen_tools.add(tid)

        # §3.7 no-resurrection guard: blocklisted tool ids and names
        # are refused wherever they turn up in the row.
        needles = [tid, str(t.get("name", "")).lower()]
        needles += [str(x).lower() for x in (t.get("tags") or [])]
        for needle in needles:
            if needle in NO_RESURRECTION:
                if needle in BLOCK_PAID:
                    findings.append(
                        "manifest-wellformed: FAIL: %s: purged tooling (§3.7 paid "
                        "licence): %r — no resurrection of excluded classes"
                        % (tid, needle)
                    )
                else:
                    findings.append(
                        "manifest-wellformed: FAIL: %s: purged tooling (§3.7 "
                        "hardware/RF class): %r — no resurrection of excluded "
                        "classes" % (tid, needle)
                    )
                return findings

        # every category exists
        category = t.get("category")
        if category not in cat_ids:
            findings.append(
                "manifest-wellformed: FAIL: %s: unknown category id %r"
                % (tid, category)
            )
            return findings
        secondary_categories = t.get("secondary_categories", [])
        if not isinstance(secondary_categories, list):
            findings.append(
                "manifest-wellformed: FAIL: %s: secondary_categories must be a "
                "list" % tid
            )
            return findings
        if any(not isinstance(x, str) for x in secondary_categories):
            findings.append(
                "manifest-wellformed: FAIL: %s: secondary_categories entry must "
                "be a str: %r"
                % (
                    tid,
                    next(
                        x
                        for x in secondary_categories
                        if not isinstance(x, str)
                    ),
                )
            )
            return findings
        for s in secondary_categories:
            if s == category:
                findings.append(
                    "manifest-wellformed: FAIL: %s: single primary category: %r "
                    "repeated in secondary_categories" % (tid, s)
                )
                return findings
            if s not in cat_ids:
                findings.append(
                    "manifest-wellformed: FAIL: %s: unknown category id %r "
                    "(secondary_categories)" % (tid, s)
                )
                return findings

        # packaging: bespoke tools carry a derivation path
        packaging = t.get("packaging") or {}
        if packaging.get("status") == "bespoke" and not packaging.get(
            "derivation"
        ):
            findings.append(
                "manifest-wellformed: FAIL: %s: bespoke tool without "
                "packaging.derivation" % tid
            )
            return findings

        # ATTACK-layer tools carry >= 1 ATLAS tactic; shaped AML.T####
        if t.get("layer") == "ATTACK":
            tactics = t.get("atlas_tactics")
            if not isinstance(tactics, list) or not any(
                isinstance(x, str) for x in tactics
            ):
                findings.append(
                    "manifest-wellformed: FAIL: %s: ATTACK-layer tool without "
                    "atlas_tactics (KA-05.1)" % tid
                )
                return findings
            for tactic in tactics:
                if not ATLAS_TOOL_PATTERN.match(tactic):
                    findings.append(
                        "manifest-wellformed: FAIL: %s: bad MITRE ATLAS technique "
                        "id shape (AML.T####): %r" % (tid, tactic)
                    )
                    return findings

        # safety.level vocabulary
        level = (t.get("safety") or {}).get("level")
        if level not in SAFETY_LEVELS:
            findings.append(
                "manifest-wellformed: FAIL: %s: invalid safety.level %r (expected "
                "one of: %s)" % (tid, level, ", ".join(sorted(SAFETY_LEVELS)))
            )
            return findings

    return findings


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

    # tools.yaml invariants (KA-05.1): the tools-table half of the gate
    # runs through the same seam the invariant suite drives
    # (tests/test_invariants.py) — unique ids, categories exist,
    # bespoke => derivation, ATTACK ATLAS coverage + id shape,
    # §3.7 no-resurrection, safety.level vocabulary. `require_nonempty`
    # stays False until the KA-05 seed lanes land rows (KA-02.2's
    # handover constraint: the empty stub is well-formed for now).
    tools_path = os.path.join(MANIFEST, "tools.yaml")
    if not os.path.exists(tools_path):
        return fail("tools.yaml missing (KA-02.2 owns it)")
    with open(tools_path) as f:
        tdoc = yaml.safe_load(f) or {}
    for tool_fail in run_tools_checks(tdoc, cat_ids=seen):
        return fail(tool_fail.split("manifest-wellformed: FAIL: ", 1)[-1])

    print(
        "manifest-wellformed: OK (%d category entries, %d tools; primary slots: %s; data-packs excluded from counts)"
        % (
            len(entries),
            len(tdoc.get("tools") or []),
            ", ".join("%s %d" % (l, n) for l, n in sorted(per_layer.items())) or "none",
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
