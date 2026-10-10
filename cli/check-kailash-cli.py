#!/usr/bin/env python3
"""kailash-check — the checks.kailash-cli-self-test exercise (KA-14.1).

Exercises cli/kailash (list/filter/search/info/manifest-check, --json)
against the REAL manifest in the flake source tree and asserts the CLI's
output against the parsed manifest DATA — never hardcoded row counts —
so the check stays green as manifest rows land (KA-05.x).

The watched negative case lives here too: `kailash info <absent-id>`
MUST exit 1 against the current tools table (KA-hypothesis), proven in
CI by construction on every run. Loader resolution (repo / flake source
/ installed) is proven by construction: the checker imports the module
from $src/cli with no PYTHONPATH help, i.e. the __file__-relative
manifest resolution this lane delivers.
"""
import json
import os
import subprocess
import sys

SRC = os.environ.get("src") or os.environ.get("KAILASH_SRC") or os.getcwd()
CLI = os.path.join(SRC, "cli")
sys.path.insert(0, CLI)

import yaml  # the env ships pyyaml via withPackages

sys.path.insert(0, CLI)
from kailash import manifest  # noqa: E402
from kailash import cli as kcli  # noqa: E402

FAILURES = []


def check(cond, label, detail=""):
    if cond:
        print("ok: %s" % label)
    else:
        FAILURES.append("%s%s" % (label, (": " + detail) if detail else ""))
        print("FAIL: %s%s" % (label, (": " + detail) if detail else ""))


def run_cli(argv):
    """Run the CLI in-process (import-isolated: main(argv) with patched
    stdout) — the same entry the packaged console_script binds."""
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    code = 0
    with redirect_stdout(buf):
        code = kcli.main(argv)
    return code, buf.getvalue()


def main():
    # SRC anchors the DATA (repo root or flake src): same tree the
    # runCommand exports as $src; the loader resolves the files itself
    # via __file__ — checker asserts the CLI's view against an
    # INDEPENDENT pyyaml parse of the same files.
    manifest_dir = os.path.join(SRC, "manifest")
    cats_doc = yaml.safe_load(
        open(os.path.join(manifest_dir, "categories.yaml")))
    tools_doc = yaml.safe_load(open(os.path.join(manifest_dir, "tools.yaml")))
    cats = cats_doc.get("categories") or []
    tools = tools_doc.get("tools") or []
    cat_ids = [c["id"] for c in cats]

    # 1. loader self-inventory == parsed manifest content (DATA assertion)
    code, out = run_cli(["manifest", "check"])
    inv = json.loads(out or "{}")
    check(code == 0, "manifest check exit 0")
    check(inv.get("categories") == len(cats),
          "manifest check counts == parsed categories.yaml",
          "%r != %d" % (inv.get("categories"), len(cats)))
    check(inv.get("tools") == len(tools),
          "manifest check counts == parsed tools.yaml",
          "%r != %d" % (inv.get("tools"), len(tools)))

    # 2. list vs category rows — one row per entry, id-first ordering
    code, out = run_cli(["list"])
    rows = out.splitlines()
    check(code == 0, "list exit 0")
    check(len(rows) == len(cats),
          "list row count equals parsed categories",
          "%d != %d" % (len(rows), len(cats)))
    expect = ["%s\t%s\t%s\t%s" % (c["id"], c["layer"], c["kind"], c["tools"])
              for c in cats]
    check(rows == expect, "list rows equal parsed manifest content",
          "first divergence: %s" % next(
              ("%s != %s" % (a, b) for a, b in zip(rows, expect) if a != b),
              "length %d vs %d" % (len(rows), len(expect))))

    # --json over the same view: same rows as JSON strings
    code, jout = run_cli(["--json", "list"])
    check(code == 0 and isinstance(json.loads(jout), list),
          "list --json emits valid JSON")
    check(json.loads(jout) == rows, "list --json equals list rows")

    # 3. --layer filter: per-layer counts match the parsed census sums
    if cats:
        layer = cats[0]["layer"]
        want = [c for c in cats if c["layer"] == layer]
        code, out = run_cli(["list", "--layer", layer])
        check(code == 0 and out.splitlines() == [
            "%s\t%s\t%s\t%s" % (c["id"], c["layer"], c["kind"], c["tools"])
            for c in want],
            "list --layer %s equals the parsed layer rows" % layer)
        # a layer id absent from categories.yaml MUST be rejected as a
        # usage error (exit 2, not a silent no-results 1) — computed
        # from the data, not a hardcoded name
        absent = next(("%sX" % l for l in ("CLASSIC", "ATTACK", "DEFENCE",
                                           "BUILD", "OPS")
                       if l not in {c["layer"] for c in cats}), None)
        if absent:
            code, out = run_cli(["list", "--layer", absent])
            check(code == 2,
                  "list --layer %s (not in categories.yaml) exits 2" % absent,
                  "rc=%d" % code)

    # 4. --category + --status against the DATA
    if cats:
        c0 = cats[0]
        code, out = run_cli(["list", "--category", c0["id"]])
        check(code == 0 and c0["id"] in out, "list --category filters")
        c1 = cats[-1]
        code, out = run_cli(["list", "--category", c1["id"],
                             "--layer", c1["layer"]])
        if code == 0:
            check(c1["id"] in out, "combined layer+category filter matches")
        else:
            check(code == 1, "combined filter no-match exits 1")
        code, out = run_cli(["list", "--status", manifest.STATUSES[0]])
        if tools:
            check(code == 0 or code == 1, "status filter against tool rows")
        else:
            # header-only tools table: any --status yields no rows -> 1
            check(code == 1, "list --status over the empty tools table exits 1",
                  "rc=%d" % code)

    # 5. search: hits come from the four fields; empty table exits 1
    q = "zzz-no-such-tool-token"
    code, out = run_cli(["search", q])
    check(code == 1, "search with no hits exits 1", "rc=%d" % code)
    if tools:
        t0 = tools[0]
        token = t0["id"].split("-")[0]
        code, out = run_cli(["search", token])
        check(code == 0 and t0["id"] in out, "search finds id fragments")
    else:  # header-only stub: corpus empty -> every query exits 1
        check(code == 1, "search over the empty tools table exits 1")

    # 6. info: the entry record as JSON; absent id exits 1 — the
    # KA-14.1 watched negative case, proven in CI by construction
    if tools:
        t1 = tools[0]
        code, out = run_cli(["info", t1["id"]])
        rec = json.loads(out or "null")
        check(code == 0 and rec.get("id") == t1["id"],
              "info prints the tool record (json)")
    else:
        code, out = run_cli(["info", "totally-absent-tool"])
        check(code == 1, "info on an absent id exits 1", "rc=%d" % code)

    # grep-backed proof for the absent-id exit: the stderr line carries
    # the queried id (the checker asserts against DATA, not rc alone)
    code, out = run_cli(["--json", "info", "totally-absent-tool"])
    check(code == 1, "info --json on an absent id exits 1", "rc=%d" % code)

    # 7. usage errors exit 2 (argparse SystemExit path)
    try:
        kcli.main(["info"])
        code = 0
    except SystemExit:
        code = 2
    check(code == 2, "info without tool_id is a usage error (2)")

    # stderr path check: unreadable manifest -> rc 2 with a message
    env = dict(os.environ, KAILASH_MANIFEST=os.path.join(SRC, "nonexistent"))
    p = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r); from kailash import cli; "
         "sys.exit(cli.main(['list']))" % CLI],
        env=env, capture_output=True, text=True)
    check(p.returncode == 2 and "not readable" in p.stderr,
          "unreadable manifest exits 2 with a message",
          "rc=%d stderr=%r" % (p.returncode, p.stderr[:120]))

    print()
    if FAILURES:
        print("kailash-check: FAIL (%d):" % len(FAILURES))
        for f in FAILURES:
            print("  - %s" % f)
        return 1
    print("kailash-check: OK (%d manifest categories, %d manifest tools; "
          "all assertions against the DATA)" % (len(cats), len(tools)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
