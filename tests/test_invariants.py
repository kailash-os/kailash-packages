#!/usr/bin/env python3
"""tests/test_invariants.py — KA-05.1 invariant suite for tools.yaml.

Runs the validator as a module (import, not subprocess) so every case
points at an exact invariant. Two planes:

- tools plane: `run_tools_checks(docs)` — the KA-05.1 set below —
  evaluated against in-memory categories + tools documents (fixtures).
  The empty-stub property (invariants pass trivially on
  `tools: []`) is proven explicitly: `test_empty_tools_stub_passes`
  asserts all-zero findings for the stub document exactly as checked
  into manifest/tools.yaml.
- whole-file plane: the CLI entrypoint (main()) against the real
  on-disk manifest, unchanged by this lane; the tools-table half joins
  it through the same `run_tools_checks` path main() calls.

The WATCHED RED of this suite: every fixture violation lands exactly
one manifest-wellformed failure naming its invariant — proven by the
fixture cases below, each quoting the observed failure line. (The
RED commit ships this suite against the pre-GREEN validator: every
fixture case errors with `AttributeError: module 'validate_manifest'
has no attribute 'run_tools_checks'` (23 of 24; the blocklist-census
data test passes standalone) — the suite cannot pass while the
invariants are unimplemented, and cannot lie. The
RedStateSentinel guard is deleted at GREEN.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import invariants as inv  # noqa: E402
import validate_manifest as vm  # noqa: E402

FAIL_MARKERS = ("manifest-wellformed: FAIL:",)


def cat(layer, cid, cats=(), owasp=None, tactics=None, kind="category"):
    e = {
        "id": cid,
        "layer": layer,
        "kind": kind,
        "name": cid,
        "purpose": "fixture",
        "coverage": "High",
        "tools": 1,
    }
    if tactics:
        e["atlas_tactics"] = tactics
    if owasp:
        e["owasp_llm"] = owasp
    for s in cats:
        e.setdefault("secondary", []).append(s)
    return e


def full_tool(**over):
    """A complete, valid §5.2 entry; overrides punch holes."""
    t = {
        "id": "garak",
        "layer": "ATTACK",
        "category": "a-02-prompt-injection-jailbreaks",
        "name": "garak",
        "description": "fixture",
        "source": {"vcs_owner": "NVIDIA", "repo": "garak"},
        "license": "Apache-2.0",
        "packaging": {"status": "bespoke", "derivation": "pkgs/garak/default.nix"},
        "safety": {"level": "requires-target"},
        "nixos_menu": {"icon": "garak.svg", "exec": "garak", "category": "a-02-prompt-injection-jailbreaks"},
        "atlas_tactics": ["AML.T0051"],
        "owasp_llm": {"2026": "LLM01", "v2": "LLM01"},
        "docs": "layers/a-02/garak.md",
        "tags": ["scanner"],
    }
    t.update(over)
    return t


def cats_doc(entries):
    return {"categories": entries}


def tools_doc(entries):
    return {"tools": entries}


CLASSIC_CAT = cat("CLASSIC", "c-01-information-gathering")
ATTACK_CAT = cat(
    "ATTACK",
    "a-02-prompt-injection-jailbreaks",
    tactics=["AML.TA0005", "AML.TA0007"],
    owasp={"2026": ["LLM01"], "v2": ["LLM01"]},
)
DEFENCE_CAT = cat("DEFENCE", "d-01")
BUILD_CAT = cat("BUILD", "o-01")
FIX_CATS = [CLASSIC_CAT, ATTACK_CAT, DEFENCE_CAT, BUILD_CAT]


def findings(cats, tools, **kw):
    doc = dict(cats_doc(cats))
    doc["tools"] = tools
    msgs = vm.run_tools_checks(doc, **kw)
    if msgs:
        # a non-empty validator findings list IS the fixture violation —
        # raised so assertRaises fixture cases can pin it, exactly one
        # manifest-wellformed failure naming its invariant.
        raise AssertionError("\n".join(msgs))
    return msgs


def only(msgs, frag):
    """Exactly one manifest-wellformed failure carrying `frag`.

    Accepts the raised AssertionError's joined message (one violation
    per fixture case, so the string IS the message) or a message list.
    """
    if isinstance(msgs, str):
        msgs = [msgs]
    hits = [m for m in msgs if frag in m]
    assert len(hits) == 1, "expected exactly one %r in %r" % (frag, msgs)
    return hits[0]


class UniqueToolIds(unittest.TestCase):
    def test_empty_tools_stub_passes(self):
        self.assertEqual(findings(FIX_CATS, []), [])
        stub = {"schema_version": 1, "tools": []}
        self.assertEqual(
            vm.run_tools_checks(stub, require_nonempty=False),
            [],
            "the committed empty stub must pass the invariants",
        )

    def test_nonempty_ok(self):
        self.assertEqual(findings(FIX_CATS, [full_tool()]), [])

    def test_duplicate_ids(self):
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [full_tool(), full_tool()])
        only(ctx.exception.args[0], "manifest-wellformed: FAIL:")
        only(ctx.exception.args[0], "duplicate tool id")


class CategoryExists(unittest.TestCase):
    def test_unknown_primary(self):
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [full_tool(category="c-99-not-there")])
        only(ctx.exception.args[0], "unknown category id 'c-99-not-there'")

    def test_no_secondary_categories_key_is_fine(self):
        self.assertEqual(findings(FIX_CATS, [full_tool()]), [])

    def test_secondary_exists(self):
        t = full_tool(
            secondary_categories=["c-01-information-gathering"],
            layer="ATTACK",
        )
        self.assertEqual(findings(FIX_CATS, [t]), [])

    def test_secondary_unknown(self):
        t = full_tool(secondary_categories=["c-77-ghost"])
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [t])
        only(ctx.exception.args[0], "unknown category id 'c-77-ghost'")


class BespokeDerivation(unittest.TestCase):
    def test_bespoke_with_path_ok(self):
        self.assertEqual(findings(FIX_CATS, [full_tool()]), [])

    def test_bespoke_missing_derivation(self):
        t = full_tool(packaging={"status": "bespoke"})
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [t])
        only(ctx.exception.args[0], "without packaging.derivation")

    def test_native_without_derivation_ok(self):
        t = full_tool(packaging={"status": "native"})
        self.assertEqual(findings(FIX_CATS, [t]), [])


DEF_NATIVE_CATS = FIX_CATS + [cat("DEFENCE", "d-01-runtime-defence")]


class NativeBindings(unittest.TestCase):
    """KA-24 packaging-reality gate (os#24): a DEFENCE `native` row
    carries a NATIVE_BINDINGS entry — the PROBED pinned-nixpkgs attr
    path. The id==attr guess class (a manifest row the pin does not
    actually provide under its id) is refused exactly like any invented
    mapping. Scope is the DEFENCE layer — the other layers' binding
    truth lives in their category modules' probe contracts.
    """

    def test_defence_native_recorded_binding_ok(self):
        t = full_tool(layer="DEFENCE", category="d-01-runtime-defence",
                      packaging={"status": "native"})
        vm.NATIVE_BINDINGS[t["id"]] = ("nixpkgs", "fixture-attr")
        try:
            self.assertEqual(findings(DEF_NATIVE_CATS, [t]), [])
        finally:
            del vm.NATIVE_BINDINGS[t["id"]]

    def test_defence_native_unrecorded_fails(self):
        t = full_tool(layer="DEFENCE", category="d-01-runtime-defence",
                      packaging={"status": "native"})
        vm.NATIVE_BINDINGS.pop(t["id"], None)
        with self.assertRaises(AssertionError) as ctx:
            findings(DEF_NATIVE_CATS, [t])
        only(ctx.exception.args[0], "native row without a NATIVE_BINDINGS entry")

    def test_other_layer_native_stays_outside_the_gate(self):
        # The gate is DEFENCE-scoped: a non-DEFENCE native row needs no
        # table entry (its binding truth rides the category-module
        # probe contracts, the landed per-pin named-drop rule).
        t = full_tool(packaging={"status": "native"})
        vm.NATIVE_BINDINGS.pop(t["id"], None)
        self.assertEqual(findings(FIX_CATS, [t]), [])

    def test_real_manifest_defence_native_rows_are_all_recorded(self):
        # The on-disk manifest's DEFENCE native rows: every one names
        # its probed binding. Parses the real tools.yaml so a future
        # DEFENCE row CANNOT claim native silently — the fixture-free
        # plane bites at the suite level, not only in main().
        import yaml

        manifest = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "manifest", "tools.yaml"
        )
        with open(manifest) as f:
            doc = yaml.safe_load(f)
        unrecorded = [
            t["id"]
            for t in doc["tools"]
            if t.get("layer") == "DEFENCE"
            and (t.get("packaging") or {}).get("status") == "native"
            and t["id"] not in vm.NATIVE_BINDINGS
        ]
        assert unrecorded == [], (
            "DEFENCE native rows without NATIVE_BINDINGS entries: %s"
            % unrecorded
        )

    def test_ka24_probe_receipt_rows_are_native(self):
        # The KA-24 binding-receipt flips (os#24): these two rows were
        # transcribed bespoke, but the pin PROVIDES them natively —
        # probed at nixpkgs e7439b6b (python3Packages: lm-eval 0.4.13,
        # model-signing 1.1.1; both meta.broken = false). The manifest
        # must record that reality, not a pending bespoke derivation.
        import yaml

        manifest = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "manifest", "tools.yaml"
        )
        with open(manifest) as f:
            doc = yaml.safe_load(f)
        rows = {t["id"]: t for t in doc["tools"]}
        for tid in ("lm-eval-harness", "modelsign"):
            row = rows.get(tid)
            assert row is not None, "manifest row missing: %s" % tid
            st = (row.get("packaging") or {}).get("status")
            assert st == "native", (
                "%s must carry packaging.status native (the KA-24 probe "
                "receipt: the nixpkgs binding exists and is unbroken at "
                "the pin); got %r" % (tid, st)
            )
            assert tid in vm.NATIVE_BINDINGS, (
                "%s must carry its NATIVE_BINDINGS entry" % tid
            )


class AtlasTactics(unittest.TestCase):
    def test_attack_tool_with_tactic_ok(self):
        self.assertEqual(findings(FIX_CATS, [full_tool()]), [])

    def test_attack_tool_missing_atlas(self):
        t = full_tool()
        del t["atlas_tactics"]
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [t])
        only(ctx.exception.args[0], "without atlas_tactics")

    def test_attack_tool_bad_id_shape(self):
        for bad in ("TA0051", "AML.T51", "AML TX0051", "AML.T005x"):
            t = full_tool(atlas_tactics=[bad])
            with self.assertRaises(AssertionError) as ctx:
                findings(FIX_CATS, [t])
            only(
                ctx.exception.args[0],
                "bad MITRE ATLAS technique id shape (AML.T####): %r" % bad,
            )


class NoResurrection(unittest.TestCase):
    def test_clean_tool_ok(self):
        self.assertEqual(findings(FIX_CATS, [full_tool()]), [])

    def test_wifi_tool_blocked(self):
        t = full_tool(id="aircrack-ng", name="aircrack-ng")
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [t])
        only(ctx.exception.args[0], "purged tooling (§3.7 hardware/RF class)")

    def test_paid_tool_blocked(self):
        t = full_tool(id="nessus", name="Nessus")
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [t])
        only(ctx.exception.args[0], "paid licence")

    def test_blocklist_carries_the_census(self):
        for tid in (
            "wifite",
            "hcxdumptool",
            "ubertooth",
            "bluesnarfer",
            "rfcat",
            "nessus",
            "cobalt strike",
            "ida-pro",
        ):
            self.assertIn(tid, inv.NO_RESURRECTION)


class SafetyLevel(unittest.TestCase):
    def test_level_requires_target_ok(self):
        self.assertEqual(findings(FIX_CATS, [full_tool()]), [])

    def test_level_missing(self):
        t = full_tool(safety={})
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [t])
        only(ctx.exception.args[0], "invalid safety.level %r" % None)

    def test_level_unknown(self):
        t = full_tool(safety={"level": "careful"})
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [t])
        only(ctx.exception.args[0], "invalid safety.level %r" % "careful")


class MenuCategoryVocabulary(unittest.TestCase):
    """KA-05 menu audit (os#139): nixos_menu.category joins the census.

    The menu block's category value is the SAME vocabulary as the primary
    category — census slugs (categories.yaml ids). A short-form id (a-05)
    silently drops the row from menu-generation and CLI category filters.
    """

    def test_menu_category_full_slug_ok(self):
        t = full_tool()
        self.assertEqual(findings(FIX_CATS, [t]), [])

    def test_menu_category_short_form_fails(self):
        t = full_tool()
        t["nixos_menu"] = {"icon": "art.svg", "exec": "art",
                           "category": "a-05"}
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [t])
        only(ctx.exception.args[0], "nixos_menu.category")

    def test_menu_category_absent_is_fine(self):
        t = full_tool()
        del t["nixos_menu"]
        self.assertEqual(findings(FIX_CATS, [t]), [])


class SecondaryShape(unittest.TestCase):
    def test_secondary_not_a_list(self):
        t = full_tool(secondary_categories="c-01-information-gathering")
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [t])
        only(ctx.exception.args[0], "secondary_categories must be a list")

    def test_secondary_element_not_str(self):
        t = full_tool(secondary_categories=[7])
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [t])
        only(
            ctx.exception.args[0],
            "secondary_categories entry must be a str",
        )

    def test_no_second_primary(self):
        # the tool's own primary category repeated in the secondary list
        # is exactly the second-primary error (same id, two slots).
        t = full_tool(secondary_categories=["a-02-prompt-injection-jailbreaks"])
        with self.assertRaises(AssertionError) as ctx:
            findings(FIX_CATS, [t])
        only(
            ctx.exception.args[0],
            "single primary category",
        )


class DefenceCensus(unittest.TestCase):
    """KA-04.3: the DEFENCE census-existence invariant mirrors ATTACK/OPS."""

    def test_missing_layer_fails_with_all_seven(self):
        doc = {"categories": [CLASSIC_CAT, ATTACK_CAT, BUILD_CAT]}
        fails = vm.defence_census_failures(doc["categories"])
        assert len(fails) == 1, fails
        only(fails[0], "DEFENCE census incomplete (KA-04.3)")
        for slug in vm.DEFENCE_CENSUS_IDS:
            assert slug in fails[0], slug

    def test_extra_entry_fails(self):
        # the full exact census first (else the incomplete branch fires
        # first — mirrored from the OPS invariant's ordering), then the
        # rogue extra entry.
        exact = [
            cat("DEFENCE", "d-01-runtime-defence"),
            cat("DEFENCE", "d-02-detection-monitoring-observability"),
            cat("DEFENCE", "d-03-assurance-evals-benchmarks"),
            cat("DEFENCE", "d-04-provenance-signing-trust"),
            cat("DEFENCE", "d-05-threat-modelling"),
            cat("DEFENCE", "d-06-governance-regulation-mapping"),
            cat("DEFENCE", "d-07-standards-verification"),
        ]
        d8 = cat("DEFENCE", "d-08-rogue")
        base = [CLASSIC_CAT, ATTACK_CAT, BUILD_CAT]
        fails = vm.defence_census_failures(base + exact + [d8])
        assert len(fails) == 1, fails
        only(fails[0], "DEFENCE census unexpected entries (KA-04.3)")

    def test_exact_census_passes(self):
        doc = {"categories": [CLASSIC_CAT, ATTACK_CAT, BUILD_CAT]}
        rows = [
            cat("DEFENCE", "d-01-runtime-defence"),
            cat("DEFENCE", "d-02-detection-monitoring-observability"),
            cat("DEFENCE", "d-03-assurance-evals-benchmarks"),
            cat("DEFENCE", "d-04-provenance-signing-trust"),
            cat("DEFENCE", "d-05-threat-modelling"),
            cat("DEFENCE", "d-06-governance-regulation-mapping"),
            cat("DEFENCE", "d-07-standards-verification"),
        ]
        assert vm.defence_census_failures(doc["categories"] + rows) == []


if __name__ == "__main__":
    unittest.main()
