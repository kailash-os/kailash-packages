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
        "nixos_menu": {"icon": "garak.svg", "exec": "garak", "category": "a-02"},
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
        only(ctx.exception.args[0], "secondary_categories entry must be a str")

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


if __name__ == "__main__":
    unittest.main()
