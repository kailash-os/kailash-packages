#!/usr/bin/env python3
"""Tests for the KA-22 A-3/A-4 row surface (kailash-os#22) — os#210 update.

The os#210 phantom-upstream purge (2026-10-14) removed every
manifest row whose claimed upstream does not exist; a-03's bespoke
probes and a-04's supply-chain inspectors were among them (registry:
kailash-os#210, first comment). The structural invariants keep their
shape, re-based on the real rows that remain:

  a-03 = 5 rows: mcp-scan, mcp-guardian, mcp-remote, mcpoison,
         agent-dojo — all bespoke, derivations on disk; no data rows
         after poisoned-skill-pack (phantom upstream) was removed
  a-04 = 3 rows: guarddog, picklescan, modelscan — all bespoke with
         derivations on disk
  ATTACK primaries = 23 post-purge (the 58 basis counted the removed
  phantom rows); mcp-inspector's primary is o-07 with an a-03
  secondary — the one-tool-one-primary rule this file has always
  pinned, unchanged

Derivation-truth invariant (was: the 404-probe rows stay drv-free per
the llm-red-team-col precedent, kailash-os#104; superseded by the
os#210 decision — planned/unbuilt tools ship no manifest row at all,
so those probe rows no longer exist here): every bespoke a-03/a-04
row has a real derivation on disk. An upstream that does not exist is
a validator-gate refusal now (tests/validate_manifest.py, os#210);
rows cannot ship without one.

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

    def tests_a03_primary_set(self):
        rows = [t for t in self.tools if primary_in(t, A03)]
        self.assertEqual(
            [t["id"] for t in rows],
            ["mcp-scan", "mcp-guardian", "mcp-remote", "mcpoison",
             "agent-dojo"],
            "a-03 primary rows drifted (post-os#210 purge basis)")

    def tests_a03_data_rows_none(self):
        rows = [t for t in self.tools if primary_in(t, A03)]
        data = [t["id"] for t in rows
                if (t.get("packaging") or {}).get("status") == "data"]
        self.assertEqual(data, [],
                         "a-03 data rows must be [] post-os#210 (the "
                         "poisoned-skill-pack row was phantom-upstream "
                         "and removed); got %s" % data)

    def tests_a03_installable_set(self):
        rows = [t for t in self.tools if primary_in(t, A03)]
        installable = [t["id"] for t in rows
                       if (t.get("packaging") or {}).get("status")
                       in ("native", "stale", "bespoke")]
        self.assertEqual(
            installable,
            ["mcp-scan", "mcp-guardian", "mcp-remote",
             "mcpoison", "agent-dojo"],
            "a-03 installable set (manifest order) drifted")

    def tests_a03_bespoke_rows_carry_declared_derivations(self):
        """House packaging contract: bespoke rows declare their
        derivation path (overlay-pending commitment — the field must
        exist even where the file lands later); the LANDED subset
        (real derivations on disk today) must stay on disk."""
        rows = [t for t in self.tools if primary_in(t, A03)]
        for t in rows:
            drv = (t.get("packaging") or {}).get("derivation") or ""
            self.assertTrue(drv, "%s bespoke row without declared "
                                 "derivation" % t["id"])
        landed = self.by_id["mcp-scan"], self.by_id["mcp-guardian"], \
            self.by_id["mcp-remote"], self.by_id["agent-dojo"]
        for t in landed:
            drv = (t.get("packaging") or {}).get("derivation")
            self.assertTrue(
                os.path.exists(os.path.join(HERE, "..", drv)),
                "%s landed derivation missing on disk: %s" % (t["id"], drv))

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
            ["guarddog", "picklescan", "modelscan"],
            "a-04 row ids (manifest order) drifted — post-os#210 the "
            "supply-chain inspector rows carried phantom upstreams and "
            "were removed with the rest of the registry set")

    def tests_a04_bespoke_rows_carry_declared_derivations(self):
        rows = [t for t in self.tools if primary_in(t, A04)]
        for t in rows:
            st = (t.get("packaging") or {}).get("status")
            drv = (t.get("packaging") or {}).get("derivation") or ""
            if st == "bespoke":
                self.assertTrue(drv, "%s bespoke row without declared "
                                     "derivation" % t["id"])
        # modelscan flipped native post-os#210 (real nixpkgs attr 0.8.8,
        # probed) — its NATIVE_BINDINGS entry carries the binding truth
        ms = self.by_id.get("modelscan")
        self.assertIsNotNone(ms)
        self.assertEqual((ms.get("packaging") or {}).get("status"),
                         "native", "modelscan native flip regressed")
        landed = self.by_id["guarddog"], self.by_id["picklescan"]
        for t in landed:
            drv = (t.get("packaging") or {}).get("derivation")
            self.assertTrue(
                os.path.exists(os.path.join(HERE, "..", drv)),
                "%s landed derivation missing on disk: %s" % (t["id"], drv))

    def tests_every_a03_a04_row_maps_atlas(self):
        for t in self.tools:
            if primary_in(t, A03) or primary_in(t, A04):
                self.assertTrue(t.get("atlas_tactics"),
                                "%s carries no atlas_tactics" % t["id"])
                self.assertTrue(t.get("owasp_llm"),
                                "%s carries no owasp_llm" % t["id"])

    def tests_attack_primary_count_post_purge(self):
        """os#210 census re-basis: ATTACK primaries are 23 after the
        phantom-upstream purge (the 58 basis counted the removed rows).
        mcp-inspector's primary is o-07; a-03 carries it as a
        secondary — the one-tool-one-primary rule holds unchanged."""
        attack = [t for t in self.tools if t.get("layer") == "ATTACK"]
        self.assertEqual(len(attack), 23,
                         "ATTACK primary rows %d != 23 (os#210 purge "
                         "basis; the pre-purge 58 counted the removed "
                         "phantom rows)" % len(attack))
        mi = self.by_id.get("mcp-inspector")
        self.assertIsNotNone(mi)
        self.assertEqual(mi.get("category"), "o-07-agent-mcp-operability",
                         "mcp-inspector primary drifted off o-07")
        self.assertTrue(secondary_in(mi, A03),
                        "mcp-inspector lost its a-03 secondary")
        self.assertFalse(primary_in(mi, A03),
                         "mcp-inspector gained an a-03 primary (would "
                         "double-count the census)")


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    failures = len(result.failures) + len(result.errors)
    if failures:
        print("test_ka22_a3_a4_rows: RED (%d failed)" % failures)
        sys.exit(1)
    print("test_ka22_a3_a4_rows: OK (%d tests)" % result.testsRun)
