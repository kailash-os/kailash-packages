"""kailash CLI — list / search / info over the two manifest files.

KA-14.1 (plan §7.1–7.4): the commands read the manifest and print; the
nix shelling-out commands (shell/enable/doctor/...) are later KA-14
children's surface. Machine-readable posture per §7.4: every command
carries --json (stable JSON shape, null for absent fields) — accepted
before or after the subcommand.

Exit codes:
  0  results printed
  1  no results (info on an absent id included)
  2  usage error (argparse) or unreadable/unparsable manifest

Constituency: tool rows come from manifest/tools.yaml, the category tree
(ids per layer) from manifest/categories.yaml; the §5.2 invariants live
in tests/validate_manifest.py, never duplicated here.
"""
import argparse
import json
import sys

from . import manifest

PROG = "kailash"


def _emit(rows, as_json):
    """Print one row per line; --json swaps in the machine-readable form."""
    if as_json:
        json.dump(rows, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    else:
        for row in rows:
            sys.stdout.write(row + "\n")


def _fail(msg, code=2):
    sys.stderr.write("%s: %s\n" % (PROG, msg))
    return code


# ---- commands ----------------------------------------------------------


def cmd_list(args):
    """kailash list [--layer L] [--category C] [--status S] [--json].

    Category-tree view while the tools table has no rows (its header-only
    stub stands until KA-05.x fills it): one row per categories.yaml
    entry — id, layer, kind, tools (primary tool slots, the census
    count). Tool rows take over as the table lands; filters apply to
    whichever view printed. Rows come from the manifest — nothing is
    hardcoded, so the command stays green as manifest rows land.
    """
    try:
        cats = manifest.load_categories()
        tools = manifest.load_tools()
    except manifest.ManifestError as exc:
        return _fail(str(exc))

    if args.layer and args.layer not in {c["layer"] for c in cats}:
        return _fail(
            "unknown layer '%s' (categories.yaml defines: %s)"
            % (args.layer, ", ".join(sorted({c["layer"] for c in cats})))
        )

    rows = []
    if tools:
        for t in tools:
            if args.layer and t.get("layer") != args.layer:
                continue
            if args.category and t.get("category") != args.category:
                continue
            status = (t.get("packaging") or {}).get("status")
            if args.status and status != args.status:
                continue
            rows.append("%s\t%s\t%s\t%s" % (
                t.get("id"), t.get("layer"), t.get("category"), status))
    else:
        # tools table not landed yet (KA-05.x): the census is the
        # categories tree. --status filters on tool packaging.status —
        # the header-only table has none, so any --status here yields
        # no rows (exit 1), never a mislabeled category row.
        for c in cats:
            if args.layer and c["layer"] != args.layer:
                continue
            if args.category and c["id"] != args.category:
                continue
            if args.status:  # no tool rows exist to carry a status
                continue
            rows.append("%s\t%s\t%s\t%s" % (
                c["id"], c["layer"], c["kind"], c["tools"]))

    if not rows:
        return _fail("no results", code=1)
    _emit(rows, args.json)
    return 0


def cmd_search(args):
    """kailash search <query> [--json] — id, name, description, tags.

    Case-insensitive substring match across the four fields; with the
    header-only tools stub the searchable corpus is empty and every
    query exits 1 no-results.
    """
    try:
        rows_src = manifest.load_tools()
    except manifest.ManifestError as exc:
        return _fail(str(exc))

    q = args.query.lower()
    hits = []
    for t in rows_src:
        hay = (
            t.get("id"),
            t.get("name"),
            t.get("description"),
            " ".join(t.get("tags") or []),
        )
        if any(isinstance(h, str) and q in h.lower() for h in hay):
            hits.append("%s\t%s\t%s" % (
                t.get("id"), t.get("name"), t.get("description")))

    if not hits:
        return _fail("no results", code=1)
    _emit(hits, args.json)
    return 0


def cmd_info(args):
    """kailash info <tool-id> [--json] — the manifest record as JSON.

    Prints the full tools.yaml entry for the named id; an absent id
    exits 1 (the header-only stub has an empty list, so every id is
    absent for now — the KA-05.x table fills it).
    """
    try:
        rows_src = manifest.load_tools()
    except manifest.ManifestError as exc:
        return _fail(str(exc))

    for t in rows_src:
        if t.get("id") == args.tool_id:
            json.dump(t, sys.stdout, sort_keys=True)
            sys.stdout.write("\n")
            return 0
    return _fail("no results: no tool id '%s' in the manifest" % args.tool_id,
                 code=1)


# ---- parser ------------------------------------------------------------


class _JsonParent(argparse.Action):
    """No-op action standing in for the top-level --json in subparsers.

    `kailash --json list` parses --json at the top level; the
    subparsers accept the same flag via _JsonParent so
    `kailash list --json` parses there. Both spellings land in the one
    args.json slot — the §7.4 flag accepted before or after the
    subcommand.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, "json_top", True)


def cmd_check(args):
    """kailash manifest check — the loader's self-inventory (KA-14 test aid).

    Machine-readability evidence: every emitted value is a JSON value the
    loader read back from the manifest, so a checker can assert against
    the DATA (grep the exact value) instead of hardcoded row counts —
    keeping the check green as manifest rows land (KA-05.x).
    """
    try:
        cats = manifest.load_categories()
        tools = manifest.load_tools()
    except manifest.ManifestError as exc:
        return _fail(str(exc))
    json.dump({"categories": len(cats), "tools": len(tools)}, sys.stdout)
    sys.stdout.write("\n")
    return 0


def build_parser():
    p = argparse.ArgumentParser(
        prog=PROG,
        description="Kailash OS manifest CLI (KA-14.1; plan §7). Commands "
                    "read the manifest; the nix-wrapper commands land with "
                    "later KA-14 children.")
    p.add_argument(
        "--json", action="store_true", default=False,
        help="emit machine-readable JSON (§7.4 posture)")
    sub = p.add_subparsers(dest="command", required=True)

    lst = sub.add_parser(
        "list",
        help="category tree (tool rows once the census lands)")
    # default=argparse.SUPPRESS: 3.9-3.11 subparsers parse into a fresh
    # namespace and copy every attribute back to the parent's — a
    # non-SUPPRESS default would clobber the top-level `kailash --json
    # list` parse with None.
    lst.add_argument("--json", action=_JsonParent, nargs=0,
                     default=argparse.SUPPRESS,
                     help="emit machine-readable JSON (§7.4 posture)")
    lst.add_argument("--layer", help="filter by layer (categories.yaml ids: "
                                     "CLASSIC|ATTACK|DEFENCE|BUILD)")
    lst.add_argument("--category", help="filter by category id")
    lst.add_argument(
        "--status", choices=manifest.STATUSES,
        help="filter on tool packaging.status (§5.2)")
    lst.set_defaults(func=cmd_list)

    sea = sub.add_parser("search",
                         help="search over id, name, description, tags")
    sea.add_argument("query")
    sea.add_argument("--json", action=_JsonParent, nargs=0,
                     default=argparse.SUPPRESS,
                     help="emit machine-readable JSON (§7.4 posture)")
    sea.set_defaults(func=cmd_search)

    inf = sub.add_parser("info",
                         help="print one tool's manifest record as JSON")
    inf.add_argument("tool_id")
    inf.add_argument("--json", action=_JsonParent, nargs=0,
                     default=argparse.SUPPRESS,
                     help="emit machine-readable JSON (§7.4 posture)")
    inf.set_defaults(func=cmd_info)

    man = sub.add_parser("manifest", help="manifest subcommands")
    mansub = man.add_subparsers(dest="manifest_command", required=True)
    mansub.add_parser("validate", help="run the repo validator (KA-14.2)")
    chk = mansub.add_parser("check", help="loader self-inventory as JSON "
                                           "(counts read back from the files)")
    chk.set_defaults(func=cmd_check)
    man.set_defaults(func=None)
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(
        argv if argv is not None else sys.argv[1:])
    args.json = getattr(args, "json", False) or getattr(args, "json_top", False)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 2


if __name__ == "__main__":
    sys.exit(main())
