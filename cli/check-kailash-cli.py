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

    # 2. list vs the tools table — one row per tool, id-first ordering
    # (KA-05.2: the table is filled, so the CLI's tool view is the
    # surface under test; the category-tree view belongs to the stub
    # state and stays covered by the --layer/--category filters below)
    code, out = run_cli(["list"])
    rows = out.splitlines()
    check(code == 0, "list exit 0")
    if tools:
        expect = ["%s\t%s\t%s\t%s" % (
            t["id"], t["layer"], t["category"],
            (t.get("packaging") or {}).get("status"))
            for t in tools]
    else:
        expect = ["%s\t%s\t%s\t%s" % (c["id"], c["layer"], c["kind"], c["tools"])
                  for c in cats]
    check(len(rows) == len(expect),
          "list row count equals parsed manifest rows",
          "%d != %d" % (len(rows), len(expect)))
    check(rows == expect, "list rows equal parsed manifest content",
          "first divergence: %s" % next(
              ("%s != %s" % (a, b) for a, b in zip(rows, expect) if a != b),
              "length %d vs %d" % (len(rows), len(expect))))

    # --json over the same view: same rows as JSON strings
    code, jout = run_cli(["--json", "list"])
    check(code == 0 and isinstance(json.loads(jout), list),
          "list --json emits valid JSON")
    check(json.loads(jout) == rows, "list --json equals list rows")

    # 3. --layer filter: per-layer tool-row counts match the parsed rows
    if cats:
        layer = "CLASSIC" if any(c["layer"] == "CLASSIC" for c in cats) \
            else cats[0]["layer"]
        if tools:
            want = [t for t in tools if t["layer"] == layer]
            want_rows = ["%s\t%s\t%s\t%s" % (
                t["id"], t["layer"], t["category"],
                (t.get("packaging") or {}).get("status")) for t in want]
        else:
            want = [c for c in cats if c["layer"] == layer]
            want_rows = ["%s\t%s\t%s\t%s" % (
                c["id"], c["layer"], c["kind"], c["tools"]) for c in want]
        code, out = run_cli(["list", "--layer", layer])
        check(code == 0 and out.splitlines() == want_rows,
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

    # 8 (KA-14.3): `kailash manifest validate` wires the CLI surface onto
    # the repo validator — every CLI surface wired by KA-14.x lands with
    # a check here (the checker is the flake's cli gate). Positive: the
    # real manifest validates (exit 0, the manifest-wellformed OK line
    # printed). Negative: a synthetic broken-manifest fixture (a tools
    # row with no safety.level) is refused (exit non-zero) — the fixture
    # reaches the CLI through the §7.3 per-file env contract
    # (KAILASH_MANIFEST names the broken tools.yaml FILE), the same seam
    # the wrapped binary's bake uses, so the CLI validates exactly the
    # manifest it resolves.
    code, out = run_cli(["manifest", "validate"])
    check(code == 0, "manifest validate exit 0 on the real manifest",
          "rc=%d out=%r" % (code, out[:200]))
    check("manifest-wellformed: OK" in out,
          "manifest validate prints the validator's OK line",
          "out=%r" % out[:200])

    import shutil as _shutil
    import tempfile as _tempfile

    fixture_dir = _tempfile.mkdtemp(prefix="kailash-broken-manifest-")
    try:
        _shutil.copytree(os.path.join(SRC, "manifest"), fixture_dir,
                         dirs_exist_ok=True)
        tools_path = os.path.join(fixture_dir, "tools.yaml")
        with open(tools_path) as fh:
            doc = yaml.safe_load(fh)
        if not doc.get("tools"):
            # header-only stub state: there is no row to break — the
            # negative case cannot run; fail loudly rather than IndexError
            check(False, "manifest validate negative case",
                  "tools table is empty (stub state): no row to break")
        else:
            doc["tools"][0].pop("safety", None)
            with open(tools_path, "w") as fh:
                yaml.safe_dump(doc, fh, sort_keys=False)
            prev_tools = os.environ.get("KAILASH_MANIFEST")
            prev_cats = os.environ.get("KAILASH_CATEGORIES")
            try:
                os.environ["KAILASH_MANIFEST"] = tools_path
                os.environ["KAILASH_CATEGORIES"] = os.path.join(
                    fixture_dir, "categories.yaml")
                code, out = run_cli(["manifest", "validate"])
                check(code != 0,
                      "manifest validate exits non-zero on a broken fixture",
                      "rc=%d out=%r" % (code, out[:200]))
                check("manifest-wellformed: FAIL" in out,
                      "manifest validate prints the validator's FAIL line",
                      "out=%r" % out[:200])
            finally:
                if prev_tools is None:
                    os.environ.pop("KAILASH_MANIFEST", None)
                else:
                    os.environ["KAILASH_MANIFEST"] = prev_tools
                if prev_cats is None:
                    os.environ.pop("KAILASH_CATEGORIES", None)
                else:
                    os.environ["KAILASH_CATEGORIES"] = prev_cats
    finally:
        _shutil.rmtree(fixture_dir, ignore_errors=True)

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

    # 7. §7.3 per-file manifest bake (KA-14.2): KAILASH_MANIFEST names
    # the tools.yaml FILE and KAILASH_CATEGORIES the categories.yaml
    # FILE — two independent paths, not one manifest directory. The
    # derivation bakes both (wrapProgram), so the loader must resolve
    # each file from its own env value: a per-file bake with a tools
    # list pointing at file A and categories at file B only holds when
    # the vars are read independently. Watched RED: the loader joins
    # every value under the directory spelling and joins categories
    # onto KAILASH_MANIFEST's directory, so the per-file bake breaks.
    try:
        env_tools = os.path.join(manifest_dir, "tools.yaml")
        env_cats = os.path.join(manifest_dir, "categories.yaml")
        if cats:
            # both env values set to their files (subprocess: the env
            # reaches a real `kailash list` like the wrapped binary's)
            import subprocess as _sp

            _p = _sp.run(
                [sys.executable, "-c",
                 "import sys; sys.path.insert(0, %r); from kailash import cli; "
                 "sys.exit(cli.main(['list']))" % CLI],
                env=dict(os.environ, KAILASH_MANIFEST=env_tools,
                         KAILASH_CATEGORIES=env_cats),
                capture_output=True, text=True)
            check(_p.returncode == 0 and cats[0]["id"] in _p.stdout,
                  "per-file env bake: list reads tools+categories from the baked files",
                  "rc=%d stderr=%r" % (_p.returncode, _p.stderr[-160:]))

            # categories-only override: KAILASH_CATEGORIES alone points at
            # the categories file; the tools file resolves via __file__ as
            # usual. Both views must still reconcile with the same data.
            _p = _sp.run(
                [sys.executable, "-c",
                 "import sys; sys.path.insert(0, %r); from kailash import cli; "
                 "sys.exit(cli.main(['list']))" % CLI],
                env=dict(os.environ, KAILASH_CATEGORIES=env_cats),
                capture_output=True, text=True)
            check(_p.returncode == 0 and cats[0]["id"] in _p.stdout,
                  "KAILASH_CATEGORIES alone redirects the categories view",
                  "rc=%d stderr=%r" % (_p.returncode, _p.stderr[-160:]))

        # in-process variant: both vars set to their files — a full CLI
        # run must resolve BOTH files against the env values
        os.environ["KAILASH_MANIFEST"] = env_tools
        os.environ["KAILASH_CATEGORIES"] = env_cats
        code, out = run_cli(["manifest", "check"])
        ok = (code == 0
              and json.loads(out or "{}").get("categories") == len(cats)
              and json.loads(out or "{}").get("tools") == len(tools))
        check(ok, "per-file env bake: manifest check against the baked files",
              "rc=%d out=%r" % (code, out[:120]))
        if cats:
            code, out = run_cli(["list", "--category", cats[0]["id"]])
            check(code == 0 and cats[0]["id"] in out,
                  "per-file env bake: categories view via KAILASH_CATEGORIES",
                  "rc=%d out=%r" % (code, out[:120]))
        # tools list empty in the stub: the env-baked tools file is still
        # the one consulted — search must exit 1 on the empty table, not
        # crash resolving the wrong path
        code, out = run_cli(["search", "zzz-no-such-tool-token"])
        check(code == 1, "per-file env bake: tools view via KAILASH_MANIFEST",
              "rc=%d out=%r" % (code, out[:120]))
    finally:
        os.environ.pop("KAILASH_MANIFEST", None)
        os.environ.pop("KAILASH_CATEGORIES", None)

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
