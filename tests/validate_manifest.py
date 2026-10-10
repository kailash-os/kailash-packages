#!/usr/bin/env python3
"""manifest-wellformed check — the overlay's manifest gate (KA-02.2 #67).

Growth path: KA-04.1 added the categories structural invariants; KA-02.2
adds the tools.yaml table to the gate (schema presence: file, YAML, schema
header, tools list; entries stay optional until KA-05 fills them);
KA-05.1 adds the full tool-entry invariants (unique ids, categories exist,
bespoke => derivation path, ATTACK >= 1 ATLAS tactic, purge-resurrection
guard).

Tools invariants (KA-02.2, entry-level full set at KA-05.1):
  - tools.yaml exists and parses as YAML
  - top-level mapping carrying schema_version: 1 and a `tools` list
  - the tools list may be empty at the stub stage (header-only manifest)
  - every present entry's keys stay inside the §5.2 field vocabulary
    (typo guard; the full field-completeness invariants land at KA-05.1)

Categories invariants (KA-04.1):
  - the file exists and parses as YAML
  - top-level schema_version: 1 and a non-empty `categories` list
  - every entry carries: id, layer, kind, name, purpose, coverage, tools
  - layer is CLASSIC | ATTACK | DEFENCE | BUILD (CORE is the substrate)
  - kind is category | data-pack; data-pack entries are opt-in
  - ids are unique
  - per-layer primary-slot totals equal the §3.6 census (data-packs
    excluded from the sums)
"""
import os
import sys

try:
    import yaml
except ImportError:  # main() reports the gate-env defect
    yaml = None

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "..", "manifest")

LAYERS = {"CLASSIC", "ATTACK", "DEFENCE", "BUILD"}
KINDS = {"category", "data-pack"}
CAT_REQUIRED = ("id", "layer", "kind", "name", "purpose", "coverage", "tools")

# §5.2 tool manifest field vocabulary — one primary category per tool.
TOOL_FIELDS = (
    "id",
    "layer",
    "category",
    "secondary_categories",
    "name",
    "description",
    "source",  # {vcs_owner, repo, vcs_url}
    "license",
    "packaging",  # {status: native | stale | bespoke | module | data, derivation}
    "safety",  # {level: safe | requires-target | exp, target-required}
    "nixos_menu",  # {icon, exec, category}
    "atlas_tactics",
    "owasp_llm",
    "docs",
    "tags",
)


def fail(msg: str) -> int:
    print("manifest-wellformed: FAIL:", msg)
    return 1


def load_yaml(path: str):
    """Parse a YAML file, turning parse errors into clean gate failures."""
    with open(path) as f:
        try:
            return yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise ValueError("YAML parse error: %s" % exc)


def check_categories():
    cats_path = os.path.join(MANIFEST, "categories.yaml")
    if not os.path.exists(cats_path):
        return fail("categories.yaml missing (KA-04.1 owns it)")
    try:
        doc = load_yaml(cats_path)
    except ValueError as exc:
        return fail("categories.yaml: %s" % exc)
    if not isinstance(doc, dict):
        return fail("categories.yaml: top-level mapping missing")

    if doc.get("schema_version") != 1:
        return fail("categories.yaml: schema_version missing or not 1")

    entries = doc.get("categories")
    if not isinstance(entries, list):
        return fail("categories.yaml: top-level 'categories' list missing")
    if not entries:
        return fail("categories.yaml: no entries")

    seen = set()
    per_layer = {}
    for e in entries:
        if not isinstance(e, dict):
            return fail("entry is not a mapping: %r" % (e,))
        for k in CAT_REQUIRED:
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
    return {"entries": len(entries), "per_layer": per_layer}


def check_tools():
    """KA-02.2: the tool table joins the gate. Entry invariants at KA-05.1."""
    tools_path = os.path.join(MANIFEST, "tools.yaml")
    if not os.path.exists(tools_path):
        return fail("tools.yaml missing (KA-02.2 owns it)")
    try:
        doc = load_yaml(tools_path)
    except ValueError as exc:
        return fail("tools.yaml: %s" % exc)
    if not isinstance(doc, dict):
        return fail("tools.yaml: top-level mapping missing")

    if doc.get("schema_version") != 1:
        return fail("tools.yaml: schema_version missing or not 1")

    tools = doc.get("tools")
    if not isinstance(tools, list):
        return fail("tools.yaml: top-level 'tools' list missing")

    for t in tools:
        if not isinstance(t, dict):
            return fail("tool entry is not a mapping: %r" % (t,))
        if not t.get("id"):
            return fail("tool entry missing id")
        for k in t:
            if k not in TOOL_FIELDS:
                return fail(
                    "tool entry %r: unknown field '%s' (§5.2 vocabulary)"
                    % (t["id"], k)
                )
    return {"entries": len(tools)}


def main() -> int:
    if yaml is None:
        print("pyyaml unavailable in check env")
        return 1

    cats = check_categories()
    if isinstance(cats, int):
        return cats
    tools = check_tools()
    if isinstance(tools, int):
        return tools

    per_layer = ", ".join(
        "%s %d" % (l, n) for l, n in sorted(cats["per_layer"].items())
    )
    header_only = "header-only (%d entries)" % tools["entries"]
    print(
        "manifest-wellformed: OK (%d entries; primary slots: %s; tools table: %s; "
        "data-packs excluded from counts)"
        % (cats["entries"], per_layer or "none", header_only)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
