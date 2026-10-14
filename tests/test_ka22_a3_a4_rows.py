#!/usr/bin/env python3
"""Tests for the KA-22 A-3/A-4 row surface (kailash-os#22, spec §8 Phase 5).

Data-driven row assertions over the parsed manifest — the counts and
membership this lane's categories must present. Nothing hardcoded on
the far side of the assert: expected values derive from the parsed
tools.yaml itself where the invariant is structural (one primary per
row; data rows never installable), and the census-pinned numbers
(a-03 = 9 rows with exactly one data row; a-04 = 8 rows, all
installable; the ATTACK 58 not 59 rule — mcp-inspector's primary is
o-07, a-03 carries it as a secondary) are the §3.6 census pins the
manifest's own header records.

Run: python3 tests/test_ka22_a3_a4_rows.py (or via unittest discovery).
Exits 0 green / 1 red; one failure line per violated assertion.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import yaml  # noqa: E402  (flake-check legs build python3.withPackages ps.pyyaml)

MANIFEST = os.path.join(HERE, "..", "manifest", "tools.yaml")


def load_tools():
    with open(MANIFEST, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh.read()) or {}
    tools = doc.get("tools") or []
    return [t for t in tools if isinstance(t, dict)]


def primary_in(t, cat):
    return t.get("category") == cat


def secondary_in(t, cat):
    secs = t.get("secondary_categories") or []
    return cat in secs


A03 = "a-03-agentic-mcp-tool-use"
A04 = "a-04-model-supply-chain"


class Ka22A3A4RowSurface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tools = load_tools()
        cls.by_id = {t["id"]: t for t in cls.tools}

    def tests_a03_primary_count_is_9(self):
        rows = [t for t in self.tools if primary_in(t, A03)]
        self.assertEqual(
            len(rows), 9,
            "a-03 primary rows %d != 9 census (kailash-os#22 KA-22)" % len(rows))

    def tests_a04_primary_count_is_8(self):
        rows = [t for t in self.tools if primary_in(t, A04)]
        self.assertEqual(
            len(rows), 8,
            "a-04 primary rows %d != 8 census (kailash-os#22 KA-22)" % len(rows))

    def tests_a03_data_row_exactly_poisoned_skill_pack(self):
        rows = [t for t in self.tools if primary_in(t, A03)]
        data = [t["id"] for t in rows
                if (t.get("packaging") or {}).get("status") == "data"]
        self.assertEqual(data, ["poisoned-skill-pack"],
                         "the a-03 data rows must be exactly "
                         "[poisoned-skill-pack]; got %s" % data)

    def tests_a03_installable_set(self):
        rows = [t for t in self.tools if primary_in(t, A03)]
        installable = [t["id"] for t in rows
                       if (t.get("packaging") or {}).get("status")
                       in ("native", "stale", "bespoke")]
        self.assertEqual(
            installable,
            ["mcp-scan", "mcp-guardian", "mcp-remote",
             "mcp-unsafe-deser-probe", "langchain-vuln-hunter",
             "llm-agent-fuzzer", "mcpoison", "agent-dojo"],
            "a-03 installable set (manifest order) drifted")

    def tests_a04_all_installable(self):
        rows = [t for t in self.tools if primary_in(t, A04)]
        off = [t["id"] for t in rows
               if (t.get("packaging") or {}).get("status")
               not in ("native", "stale", "bespoke")]
        self.assertEqual(off, [], "a-04 non-installable rows: %s" % off)

    def tests_a04_row_ids(self):
        rows = [t for t in self.tools if primary_in(t, A04)]
        ids = [t["id"] for t in rows]
        self.assertEqual(
            ids,
            ["guarddog", "picklescan", "modelscan",
             "gguf-template-inspector", "safetensors-checker",
             "hf-repo-inspector", "namespace-reuse-check", "torch-load-poc"],
            "a-04 row ids (manifest order) drifted")

    def tests_every_a03_a04_row_maps_atlas(self):
        for t in self.tools:
            if primary_in(t, A03) or primary_in(t, A04):
                self.assertTrue(t.get("atlas_tactics"),
                                "%s carries no atlas_tactics" % t["id"])
                self.assertTrue(t.get("owasp_llm"),
                                "%s carries no owasp_llm" % t["id"])

    def tests_attack_primary_total_is_58_not_59(self):
        """§3.6 census pin: ATTACK primaries are 58 — mcp-inspector's
        PRIMARY is o-07 (landed first; §3.1 one-tool-one-primary), a-03
        carries it as a SECONDARY. If this flips to 59 the census
        reconcile (validate_manifest LAYER_TOTALS) fails with it."""
        attack = [t for t in self.tools if t.get("layer") == "ATTACK"]
        self.assertEqual(len(attack), 58,
                         "ATTACK primary rows %d != 58 (§3.6; the 59th "
                         "census slot stays under OPS)" % len(attack))
        mi = self.by_id.get("mcp-inspector")
        self.assertIsNotNone(mi)
        self.assertEqual(mi.get("category"), "o-07-agent-mcp-operability",
                         "mcp-inspector primary drifted off o-07")
        self.assertTrue(secondary_in(mi, A03),
                        "mcp-inspector lost its a-03 secondary")
        self.assertFalse(primary_in(mi, A03),
                         "mcp-inspector gained an a-03 primary (would "
                         "double-count the census)")

    def tests_landed_pins_match_manifest_derivations(self):
        """Every bespoke A-3/A-4 row whose upstream EXISTS ships a
        derivation at pkgs/<id>/default.nix; the probe rows whose
        upstreams are 404 (llm-red-team-col precedent, kailash-os#104)
        stay derivation-free — data-driven via the six pinned ids this
        lane landed."""
        for tid in ("mcp-scan", "mcp-guardian", "mcp-remote", "agent-dojo",
                    "guarddog", "picklescan"):
            t = self.by_id[tid]
            self.assertEqual(
                (t.get("packaging") or {}).get("status"), "bespoke", tid)
            drv = (t.get("packaging") or {}).get("derivation") or ""
            self.assertTrue(drv, "%s bespoke row without derivation" % tid)
            self.assertTrue(
                os.path.exists(os.path.join(HERE, "..", drv)),
                "%s derivation missing on disk: %s" % (tid, drv))
        for tid in ("gguf-template-inspector", "safetensors-checker",
                    "hf-repo-inspector", "namespace-reuse-check",
                    "torch-load-poc", "langchain-vuln-hunter",
                    "llm-agent-fuzzer", "mcp-unsafe-deser-probe", "mcpoison"):
            drv = (self.by_id[tid].get("packaging") or {}).get("derivation")
            self.assertFalse(
                bool(drv) and os.path.exists(os.path.join(HERE, "..", drv)),
                "%s unexpectedly HAS a derivation — the 404-upstream "
                "record (kailash-os#22 lane) must be revisited" % tid)


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    failures = len(result.failures) + len(result.errors)
    if failures:
        print("test_ka22_a3_a4_rows: RED (%d failed)" % failures)
        sys.exit(1)
    print("test_ka22_a3_a4_rows: OK (%d tests)"
          % result.testsRun)
