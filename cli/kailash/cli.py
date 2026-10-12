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
import os
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
            # secondary_categories joins the haystack (KA-13.2,
            # kailash-os#104): the dual-use cross-list must be VISIBLE
            # through search — `kailash search c-08-...` surfaces
            # trufflehog (primary a-01, secondary c-08) the same way
            # the category listing would. One derivation, many tags.
            " ".join(t.get("secondary_categories") or []),
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


def cmd_profile(args):
    """kailash profile list [--json] — the KA-17.2 profile stub surface.

    DATA-DRIVEN: the profile list comes from a profiles.json file the
    §7.3 per-file env contract names — KAILASH_PROFILES (the packaged
    binary's wrapProgram bake points at the OS-pinned file; ko#115's
    OS-side follow-through generates it). Unset, the file resolves
    __file__-relative beside the package (the repo tree carries the
    committed sample at profiles/profiles.json). Neither exists →
    exit 1 with a message naming the missing KAILASH_PROFILES env, so
    an unbaked deployment diagnoses itself instead of printing a bare
    no-results.

    Stub OUTPUT shape per row (TAB-separated): <name>
    <layers-summary> <description> — exactly the parsed file's fields;
    --json emits the same rows as a JSON string list (the §7.4
    posture). Only `list` exists under `profile` for now; enable/
    shell-style profile verbs land with the profile-apply items.
    """
    try:
        rows_src = manifest.load_profiles()
    except manifest.ManifestError as exc:
        return _fail(str(exc))

    if not rows_src:
        # Absence diagnosis (§7.3 bake contract): whether the override
        # names a missing file or no var is set and the fallback does
        # not exist, the message names KAILASH_PROFILES — an unbaked
        # deployment diagnoses itself instead of printing a bare
        # no-results. (A set var whose file EXISTS but carries zero
        # entries is a data state, not absence: bare "no results".)
        if manifest.profiles_path() is None or not os.environ.get(
                "KAILASH_PROFILES"):
            return _fail(
                "no profiles found: KAILASH_PROFILES is not set or names an "
                "absent file, and no profiles/profiles.json exists beside "
                "the package (the OS-side bake generates it; see ko#115)",
                code=1)
        return _fail("no results", code=1)

    rows = ["%s\t%s\t%s" % (
        p.get("name"), p.get("layers"), p.get("description"))
        for p in rows_src]
    _emit(rows, args.json)
    return 0


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


def cmd_validate(args):
    """kailash manifest validate — runs the repo validator in-process.

    KA-14.3 (kailash-os#137): this is the CLI surface onto the CI gate —
    `kailash manifest validate` runs tests/validate_manifest.py (the
    single enforcement point for the §5.2/§3.6 manifest invariants) the
    way cli/check-kailash-cli.py imports the package: sys.path insertion
    beside the package, then in-process import, so the SAME env that
    ships pyyaml ships the validator (`kailash manifest validate runs
    the CI gate locally` — KA-14's acceptance clause).

    The validator runs against the manifest THE CLI RESOLVES — the §7.3
    per-file env contract included: KAILASH_MANIFEST/KAILASH_CATEGORIES
    overrides name the files, so a baked store path validates the baked
    bytes and a repo tree validates the repo files. Unset, resolution
    falls back to the __file__-relative sibling manifest dir both here
    and in the validator. Exit codes mirror the validator's: 0 when the
    gate passes (its OK line is printed verbatim), 1 on gate failure
    (the FAIL line printed verbatim), 2 when the validator cannot be
    located in this environment.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.join(here, os.pardir, os.pardir, "tests")
    if not os.path.isfile(os.path.join(tests_dir, "validate_manifest.py")):
        return _fail(
            "tests/validate_manifest.py not found beside the package "
            "(installed wheels carry cli/ only; the validator ships with "
            "the repo tree)",
            code=2,
        )

    sys.path.insert(0, os.path.abspath(tests_dir))
    try:
        import validate_manifest as vm  # noqa: E402

        # tests/ stays on sys.path for the CALL: the validator's blocklist
        # constant is a sibling import (from invariants import ...) inside
        # run_tools_checks — the plain-script run resolves it via
        # sys.path[0] = the script dir, and an in-process import needs the
        # same entry present when the deferred import fires.
        manifest_dir = os.path.dirname(manifest.tools_path())
        rc = vm.main(["--manifest-dir", manifest_dir])
    except ImportError as exc:
        return _fail("validator unavailable: %s" % exc)
    finally:
        try:
            sys.path.remove(os.path.abspath(tests_dir))
        except ValueError:
            pass
    sys.stdout.flush()
    sys.stderr.flush()
    return 1 if rc else 0


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

    prof = sub.add_parser(
        "profile",
        help="profile subcommands (KA-17.2 stub: list)")
    profsub = prof.add_subparsers(dest="profile_command", required=True)
    plist = profsub.add_parser(
        "list",
        help="enumerate the OS profiles from the baked profiles.json "
             "(KAILASH_PROFILES file; repo-tree sample as fallback)")
    plist.add_argument("--json", action=_JsonParent, nargs=0,
                       default=argparse.SUPPRESS,
                       help="emit machine-readable JSON (§7.4 posture)")
    plist.set_defaults(func=cmd_profile)
    prof.set_defaults(func=None)

    man = sub.add_parser("manifest", help="manifest subcommands")
    mansub = man.add_subparsers(dest="manifest_command", required=True)
    val = mansub.add_parser(
        "validate",
        help="run the repo manifest gate in-process (KA-14.3): exit 0 on a "
             "well-formed manifest, non-zero on gate failure")
    val.set_defaults(func=cmd_validate)
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
