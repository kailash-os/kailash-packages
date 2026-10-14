#!/usr/bin/env python3
"""manifest-wellformed check (KA-04.1 strictness + KA-04.2/KA-04.4 censuses).

Growth path: KA-02.2 (schema headers) hardens presence; KA-04.1 adds the
categories structural invariants below; KA-04.2 adds the ATTACK census
invariants (ATLAS + OWASP LLM:2026 presence per ATTACK category);
KA-04.4 adds the OPS census invariants (set existence for O-1…O-7,
layers renamed BUILD→OPS per the naming umbrella os#121 + mirror #9,
OPS=91 enforced exactly when present, per-layer reconcile permissive
to layers whose rows have not landed) and the in-file exclusions
ledger (spec §2.7, the no-resurrection guard, as a header comment
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
  - the deliberate-exclusions ledger (spec §2.7) is recorded in-file
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
  - KA-24 packaging-reality (os#24): packaging.status native carries a
    NATIVE_BINDINGS entry — the probed pinned-nixpkgs attr path, table
    in this file; an unprobed id==attr guess is refused
  - every ATTACK-layer tool carries >= 1 atlas_tactics entry shaped
    AML.T#### (shape-level regex guard — dataset-lookup verification
    stays the census lanes' review job)
  - §3.7 no-resurrection: purged tool ids/names are a data-driven
    blocklist (tests/invariants.py)
  - safety.level is safe | requires-target | exp
"""
import json
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

# §3.6 DEFENCE census — the category set KA-04.3 owns. The
# census-existence invariant fails the gate while the DEFENCE layer is
# still missing from categories.yaml (KA-04.3's RED), independent of
# per-entry checks. Slug spellings per the spec §3.2 module tree
# (d-01-runtime-defence … d-07-standards-verification).
DEFENCE_CENSUS_IDS = {
    "d-01-runtime-defence",
    "d-02-detection-monitoring-observability",
    "d-03-assurance-evals-benchmarks",
    "d-04-provenance-signing-trust",
    "d-05-threat-modelling",
    "d-06-governance-regulation-mapping",
    "d-07-standards-verification",
}

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
# (spec §2.7 — the no-resurrection guard, mirrored by the KA-05.1
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

# KA-05.1a upstream-realism data (os#210): the verification cache is a
# GENERATED artifact (tests/generate_upstream_cache.py — GitHub-API probe
# receipts + hand-written manual verdicts for non-GitHub upstreams). The
# validator only READS it: offline determinism preserved. Rows whose
# upstream record went stale get re-probed (cache regen), never waived —
# an allowlist sidestep would re-open the exact fabrication hole this
# gate closes, so none exists: the only sanctioned non-GitHub upstreams
# live in the cache's manual_entries with their receipts.
_UPSTREAM_CACHE_PATH = os.path.join(HERE, "upstream_verified.json")
with open(_UPSTREAM_CACHE_PATH, encoding="utf-8") as _f:
    _UPSTREAM_CACHE = json.load(_f)
UPSTREAM_VERDICTS = _UPSTREAM_CACHE["upstreams"]
UPSTREAM_VERDICTS_MANUAL = _UPSTREAM_CACHE.get("manual_entries", {})

# KA-24 packaging-reality gate (spec §4.3, os#24): every DEFENCE row
# claiming `native` names its pinned-nixpkgs attr path here — probed
# per pin with nix eval against the flake's own locked inputs, never
# assumed id==attr. Scope is the DEFENCE layer (the KA-24 lane's
# surface): other layers' native rows carry their per-pin binding
# truth in their own category modules' probe tables (the landed
# KA-06/07/08/09 contracts — a row absent at a pin is a NAMED drop
# there, not a manifest change). The gate refuses unprobed id==attr
# guesses on DEFENCE: a row may only claim native when this table
# carries its binding, so the recorded truth and the probed truth
# cannot drift apart silently. A row whose attr has moved at a new
# pin exits the table (its flip back to the honest status is the next
# lane's manifest change, riding that lane's probe receipts).
NATIVE_BINDINGS = {
    # Layer DEFENCE (d-01…d-07), probed at nixpkgs e7439b6b:
    "cosign": ("cosign",),
    "syft": ("syft",),
    "grype": ("grype",),
    "trivy": ("trivy",),
    "cyclonedx-cli": ("cyclonedx-cli",),
    "cdxgen": ("cdxgen",),
    "huggingface-evaluate": ("python3Packages", "evaluate"),
    "modelsign": ("python3Packages", "model-signing"),
    "modelscan": ("modelscan",),  # probed top-level attr, 0.8.8 (receipt: nix eval nixpkgs#modelscan.version, 2026-10-14)
    "lm-eval-harness": ("python3Packages", "lm-eval"),
    # NOTE: NOT maestro — the d-05 manifest row's upstream is
    # agentic-threat-modeling/MAESTRO (the CC-BY-SA threat-modelling
    # tool); nixpkgs' top-level `maestro` attr is the UNRELATED
    # mobile.dev UI-testing CLI (name collision). The row stays
    # bespoke (overlay-pending); a table entry here would record a
    # false binding under a colliding name.
}


def run_tools_checks(doc: dict, require_nonempty: bool = False, cat_ids=None) -> list:
    """tools.yaml invariants (KA-05.1, spec §4.2 vocabulary).

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
      - KA-24 packaging-reality (os#24): packaging.status 'native'
        carries a NATIVE_BINDINGS entry ("native row without a
        NATIVE_BINDINGS entry" — the probed pinned-nixpkgs attr path,
        never an unprobed id==attr guess)
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

        # upstream-realism gate (KA-05.1a, os#210 — user contract 2026-10-14:
        # the manifest is a catalogue of upstream-available tools ONLY). Two
        # pin tracks exist and both are honest:
        #   1. nixpkgs-pin track: NO source block — packaging.status native,
        #      truth home is the pinned nixpkgs attr (real, probed upstream).
        #   2. upstream-pin track: a source block — vcs_url must record a
        #      verdict-ok cache entry (tests/upstream_verified.json,
        #      generated by tests/generate_upstream_cache.py: GitHub-API
        #      probe + manual receipts for non-GitHub upstreams). This
        #      check is a pure in-cache lookup so offline/nix flake check
        #      stays deterministic — probing happens at cache-generation
        #      time, never at eval time.
        # The fabrication signature this gate closes: a source block whose
        # upstream does not exist, and a bespoke/data row with NO origin at
        # all (claimed first-party build, nothing to point at).
        source = t.get("source") or {}
        upstream = source.get("vcs_url") or ""
        packaging_status = (t.get("packaging") or {}).get("status")
        if not (source.get("vcs_owner") and upstream):
            if packaging_status != "native":
                findings.append(
                    "manifest-wellformed: FAIL: %s: no source block on a %s "
                    "row — a claimed build/data pack with no origin is the "
                    "phantom-row signature (os#210): native rows pin via "
                    "nixpkgs (track 1), everything else names a verified "
                    "upstream (track 2)" % (tid, packaging_status)
                )
                return findings
        elif "github.com" in upstream:
            pair = upstream.replace("https://github.com/", "").strip("/")
            entry = UPSTREAM_VERDICTS.get(pair)
            if entry is None or entry.get("verdict") != "ok":
                findings.append(
                    "manifest-wellformed: FAIL: %s: upstream %r is not in the "
                    "verified cache (tests/upstream_verified.json) or its "
                    "verdict is not ok — the upstream does not exist (phantom "
                    "row, os#210)" % (tid, pair)
                )
                return findings
        elif upstream:
            manual = UPSTREAM_VERDICTS_MANUAL
            hit = next((m for m in manual.values()
                        if m.get("vcs_url") == upstream), None)
            if hit is None or hit.get("verdict") != "ok":
                findings.append(
                    "manifest-wellformed: FAIL: %s: non-GitHub upstream %r has "
                    "no manual verdict ok in tests/upstream_verified.json"
                    % (tid, upstream)
                )
                return findings

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

        # KA-24 packaging-reality gate (spec §4.3, os#24): a DEFENCE row
        # claims `native` ONLY when NATIVE_BINDINGS carries its probed
        # attr path. Unprobed id==attr guesses are refused exactly like
        # any other invented binding — the table is the single home of
        # the probed truth for this layer, kept current by the packaging
        # lane that flips the row (probe receipts in that lane's PR
        # body). Other layers keep their per-pin binding truth in the
        # landed category-module probe contracts (the named-drop rule).
        if packaging.get("status") == "native" and t.get("layer") == "DEFENCE" and tid not in NATIVE_BINDINGS:
            findings.append(
                "manifest-wellformed: FAIL: %s: native row without a "
                "NATIVE_BINDINGS entry (KA-24 packaging-reality gate: "
                "the binding must be probed and recorded, never assumed "
                "id==attr)" % tid
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

        # nixos_menu.category joins the census (os#139): the menu block's
        # category value is the census-slug vocabulary — consumers (the
        # desktop menu generator, CLI category filters) join it against
        # categories.yaml ids, so a short-form id silently drops the row.
        menu = t.get("nixos_menu")
        if isinstance(menu, dict) and menu.get("category") is not None:
            mcat = menu.get("category")
            if mcat not in cat_ids:
                findings.append(
                    "manifest-wellformed: FAIL: %s: nixos_menu.category %r is "
                    "not a census category id (menu consumers join on the full "
                    "slug)" % (tid, mcat)
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


def defence_census_failures(entries: list) -> list:
    """KA-04.3 census-existence: the DEFENCE layer's 7-category set must
    be present (and only it) — fails while categories.yaml still carries
    no DEFENCE rows at all, where no per-entry check can fire. Mirrors
    the ATTACK/OPS census-existence blocks; the per-layer primary-slot
    total reconcile stays in main()'s §3.6 loop (46 lands with the rows,
    permissive to absence before KA-04.3).
    """
    defence_ids = {
        e["id"]
        for e in entries
        if isinstance(e, dict) and e.get("layer") == "DEFENCE"
    }
    failures = []
    missing = DEFENCE_CENSUS_IDS - defence_ids
    if missing:
        failures.append(
            "DEFENCE census incomplete (KA-04.3): missing %s"
            % ", ".join(sorted(missing))
        )
        return failures
    extra = defence_ids - DEFENCE_CENSUS_IDS
    if extra:
        failures.append(
            "DEFENCE census unexpected entries (KA-04.3): %s"
            % ", ".join(sorted(extra))
        )
    return failures


def main(argv=None) -> int:
    try:
        import yaml
    except ImportError:
        print("pyyaml unavailable in check env")
        return 1

    # --manifest-dir (KA-14.3): an optional seam for the CLI's
    # `kailash manifest validate` (kailash-os#137), which runs this
    # validator in-process against the manifest IT resolves (the §7.3
    # per-file env contract included). Default stays the file-sibling
    # manifest dir — the CI-manifest-job and checks.manifest-wellformed
    # subprocess invocation is unchanged by the seam.
    manifest_dir = MANIFEST
    if argv:
        args = list(argv)
        if "--manifest-dir" in args:
            idx = args.index("--manifest-dir")
            if idx + 1 >= len(args) or not args[idx + 1]:
                print("--manifest-dir requires a directory argument")
                return 1
            manifest_dir = args[idx + 1]

    cats_path = os.path.join(manifest_dir, "categories.yaml")
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

    # KA-04.3 census-existence: the DEFENCE layer's 7-category set must
    # be present (and only it) — mirrored seam, single failure line.
    for defence_fail in defence_census_failures(entries):
        return fail(defence_fail)

    # KA-04.4 exclusions ledger: the header must carry the in-file
    # ledger block (spec §2.7, the no-resurrection guard) and name
    # every excluded class.
    with open(cats_path) as f:
        cats_text = f.read().lower()
    if LEDGER_MARKER.lower() not in cats_text:
        return fail(
            "exclusions ledger (spec §2.7, KA-04.4) missing from "
            "categories.yaml header"
        )
    for cls in LEDGER_CLASSES:
        if cls not in cats_text:
            return fail(
                "exclusions ledger missing class %r (KA-04.4)" % cls
            )

    # §3.6 post-purge reconcile: layer primary-slot totals count CATEGORIES
    # only — data-packs (c-07 sdr-tools +6; wordlists-mega at KA-07.2) are
    # excluded, which is what makes the four totals sum to ~337. Each
    # layer's ROW PRESENCE is enforced by its own census-existence
    # invariant (ATTACK KA-04.2, DEFENCE KA-04.3, OPS KA-04.4); this
    # reconcile enforces the landed per-layer totals exactly: the
    # BUILD→OPS rename keeps OPS at 91 (os#121 naming umbrella).
    # §3.6 census pins ATTACK 59; post-KA-05.3, mcp-inspector's PRIMARY is o-07
    # (landed first on main via kp#38 — §3.1 one-tool-one-primary), with a-03 as a
    # secondary tag on that row. ATTACK primaries are therefore 58; the 59th census
    # slot is counted under OPS. Delta recorded on kp#39/kp#40 bodies + os#76.
    # KA-29 delta (kailash-os#29): C-5 gains the pw-packs DATA row
    # (rockyou.txt slice) — CLASSIC 141→142; the seclists data row
    # already counted. Delta recorded on the KA-29 PR bodies + os#29.
    # os#210 phantom purge (2026-10-14): the census baseline is 270 real
    # upstreams — declared layer totals on the category-sum basis are
    # CLASSIC 134 / ATTACK 23 / DEFENCE 25 / OPS 82 (= 264; +6 in the c-07
    # opt-in data-pack). The old 142/58/46/91 sheet counted the 66
    # phantom-upstream rows this purge removed; the validator refuses the
    # old numbers so the fabricated census cannot come back silently.
    LAYER_TOTALS = {"CLASSIC": 134, "ATTACK": 23, "DEFENCE": 25, "OPS": 82}
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
    tools_path = os.path.join(manifest_dir, "tools.yaml")
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
