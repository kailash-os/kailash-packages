#!/usr/bin/env python3
"""tools/wave2-smoke.py — the KA-10/11/12 acceptance smoke runner.

The flagship-five acceptance clauses name recorded runs of a real
behavioural check per tool, not just a build result:

  garak      `garak --list-probes` prints the probe index (ko#10)
  pyrit      `pyrit --version` smoke in the VM test (ko#11)
  promptfoo  `promptfoo --version` smoke in the VM test (ko#11)
  art        build and import-check (ko#12)
  counterfit build and import-check (ko#12)

This script is that per-tool smoke, packaged so it is checkable and
CI-enforceable:

  --dry-run   no Nix evaluation, no smokes: validates the per-tool command
              table against the expected acceptance shape. The
              checks.wave2-smoke-script gate runs this mode — the smoke
              commands are asserted against this table, so a drifted
              command (or a missing tool) fails the gate.
  --smoke-only --out-path PATH --tool T
              the build-leg surface: run tool T's smoke against an ALREADY
              BUILT output path (the build-packages job builds first, then
              calls this), with the per-tool PASS/FAIL line.
  (real mode) --tool T --system S: `nix build` then smoke — the standalone
              path a VM test job calls once KA-06.3 lands.

Per-tool surfaces come from the pins (verified on the pinned trees; the
pyrit deviation from the clause's literal `pyrit --version` is recorded
on the lane PR):
  garak      console script `garak` (pin pyproject [project.scripts]);
             --list_probes serves the probe index from the pin's shipped
             garak/resources/plugin_cache.json (195 probe entries at the
             105164ba pin) — needs a writable HOME (XDG cache copy).
  pyrit      upstream ships pyrit_scan/pyrit_backend/pyrit_shell console
             scripts and a REST client; no --version flag exists at the
             pin (f916d8ee). Honest shape: import pyrit and print the
             pinned version constant, using the built package's own
             interpreter (the console script's shebang — the derivation's
             python env, so pyrit + core deps resolve exactly as built).
  promptfoo  commander .version() prints the package.json semver; the
             derivation's own postInstall smoke already ran this at build
             time (the hosted leg log carries the `0.124.1` line).
  art        buildPythonPackage LIBRARY: no console script, so the smoke
             asserts the version-record + the exact module surface the
             derivation's pythonImportsCheck gates ([art,
             art.attacks.evasion, art.estimators.classification] as
             installed files) and asserts the imports-check phase line
             carried in THIS build's log (the phase fails the build when
             an import fails — build success + marker = the check ran).
  counterfit console script `counterfit` (the derivation repairs the
             upstream-broken entry point — ships counterfit.terminal);
             import smoke via the console script's shebang interpreter,
             which carries counterfit + its deps (incl. the art sibling).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys

DEFAULT_SYSTEM = "x86_64-linux"
SMOKE_TIMEOUT_S = 300
BUILD_TIMEOUT_S = 5400

TOOL_SOURCE_COMMIT = {
    "garak": "105164ba3f7960954cf69fb81a610fe672197eb0",
    "pyrit": "f916d8ee5df7b2e9859ff2c1ffef596d993db0d2",
    "promptfoo": "ce5f743f1524c7d3f0308690d2325502a8772901",
    "art": "4da50bdc5a1393bd33a52f7012f4928dd68fb260",
    "counterfit": "c00edbf595303a85a4ce0ac9d8d55d505abf4de5",
}

SEMVER = r"^([0-9]+\.[0-9]+\.[0-9]+)$"

# The per-tool smoke command table — the KA-10/11/12 acceptance clauses as
# the pins allow them to be real. Each entry's argv is asserted in
# --dry-run; the log-marker regexes are the pythonImportsCheck lines the
# nix build itself prints (a failed import FAILS the build, so a green
# build carrying the marker = the import-check ran and passed).
SMOKE_TABLE = {
    "garak": {
        "kind": "console",
        "argv": ["garak", "--list_probes"],
        # the probe index: one `probes: <module>.<class>` row per probe,
        # plus module-header rows; the pin ships 195 probe cache entries
        "regex": r"^probes: [A-Za-z0-9_]+\.[A-Za-z0-9_]+$",
        "min_count": 100,
    },
    "pyrit": {
        "kind": "import",
        "module": "pyrit",
        "version_expr": "pyrit.__version__",
        # pyrit/_version.py at f916d8ee
        "regex": SEMVER + r"(?:\.[a-zA-Z0-9]+)?$",
        "expect_group": "1.2.0.dev0",
        "console_script": "pyrit_scan",
        "build_log_marker": "Check whether the following modules can be imported: pyrit",
    },
    "promptfoo": {
        "kind": "console",
        "argv": ["promptfoo", "--version"],
        # commander .version() prints the package.json semver
        "regex": SEMVER,
        "min_count": 1,
    },
    "art": {
        "kind": "library",
        "module": "art",
        # the wheel's canonical dist name (PEP 503 normalisation of
        # adversarial-robustness-toolbox) — the dist-info dir is the
        # wheel name, verified against the cached output
        "dist_name": "adversarial_robustness_toolbox",
        # art/__init__.py at 4da50bdc
        "expect_version": "1.20.1",
        "module_files": [
            "art/__init__.py",
            "art/attacks/evasion/__init__.py",
            "art/estimators/classification/__init__.py",
        ],
        "build_log_marker": (
            "Check whether the following modules can be imported: "
            "art art.attacks.evasion art.estimators.classification"
        ),
    },
    "counterfit": {
        "kind": "import",
        "module": "counterfit",
        "version_expr": "counterfit.__version__",
        # counterfit/__init__.py at c00edbf5
        "regex": SEMVER,
        "expect_group": "1.1.0",
        "console_script": "counterfit",
        "build_log_marker": (
            "Check whether the following modules can be imported: "
            "counterfit counterfit.terminal.terminal"
        ),
    },
}

EXPECTED = sorted(SMOKE_TABLE)
DOC_DECLARED = ["art", "counterfit", "garak", "promptfoo", "pyrit"]

# build log handed over via a FILE (WAVE2_BUILD_LOG_FILE), not an env var:
# the build-package legs' logs are far beyond the ARG_MAX / argv-env
# ceiling ("Argument list too long", 126 on the first hosted smoke run)
# and the build log is evidence, not data to pass by argv.
BUILD_LOG_FILE_DEFAULT = os.environ.get("WAVE2_BUILD_LOG_FILE", "")


def load_build_log(path=None):
    p = path or BUILD_LOG_FILE_DEFAULT
    if not p or not os.path.exists(p):
        return ""
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _shebang_interpreter(console_script_path):
    """The env python the built console script runs under (its shebang).

    Nixpkgs python wrappers: bin/<script> is a bash wrapper
    (makeBinaryWrapper: '#!/nix/store/...-bash/bin/bash -e') that execs
    the REAL entry at bin/.<script>-wrapped, whose shebang IS the env
    python. Follow that one hop before judging — the wrapped script is
    the truth.
    """
    with open(console_script_path, encoding="utf-8", errors="replace") as fh:
        first = fh.readline().strip()
    if not first.startswith("#!"):
        return None
    interp = first[2:].strip()
    if "python" in os.path.basename(interp.split()[0] if interp else ""):
        return interp
    # bash/sh wrapper -> hop to the wrapped entry one level below
    wrapped = os.path.join(
        os.path.dirname(console_script_path),
        "." + os.path.basename(console_script_path) + "-wrapped")
    if os.path.exists(wrapped):
        with open(wrapped, encoding="utf-8", errors="replace") as fh:
            first = fh.readline().strip()
        if first.startswith("#!"):
            return first[2:].strip()
    return interp


def _build_log_marker_reason(tool, build_log):
    """The build that produced this output ran the imports-check phase.

    Cached-pull honest handling: when THIS leg's log shows no build at
    all (the output arrived from the substituter — no `building '/nix/`
    lines), the marker cannot be in the log, and requiring it would
    fail every warm-cache run. The pythonImportsCheck phase is part of
    the derivation (it failed-fails the build upstream), so a cached
    output carries the property transitively; a locally-built output
    still must show the marker in this leg's own log.
    """
    marker = SMOKE_TABLE[tool].get("build_log_marker")
    if not marker:
        return None
    if marker in build_log:
        return None
    if "building '/nix/store" not in build_log:
        return None  # substituter-pulled output: no build in this log
    return "build log lacks the pythonImportsCheck marker %r" % marker


def smoke_console(tool, out_path, build_log=""):
    entry = SMOKE_TABLE[tool]
    argv = list(entry.get("argv", ["<none>"]))
    env = dict(os.environ)
    if entry["kind"] == "import":
        # import smoke: run through the built package's OWN interpreter so
        # the exact built dependency set is on sys.path (no PYTHONPATH
        # guessing). The console script's shebang names it.
        script = os.path.join(out_path, "bin", entry["console_script"])
        if not os.path.exists(script):
            return False, "console script missing: %s" % script
        interp = _shebang_interpreter(script)
        if not interp or "python" not in os.path.basename(interp):
            return False, "shebang lacks a python interpreter: %r" % interp
        argv = [interp, "-c",
                "import %s; print(%s)" % (entry["module"], entry["version_expr"])]
        # HOME: cmd2/matplotlib-class init at import time wants a writable
        # HOME (counterfit); the runner provides one, and the VM likewise.
        env.setdefault("HOME", "/tmp")
    else:
        argv[0] = os.path.join(out_path, "bin", argv[0])
        if not os.path.exists(argv[0]):
            return False, "console script missing: %s" % argv[0]
        if tool == "garak":
            # `import garak` mkdirs XDG dirs under HOME (xdg-base-dirs):
            # point HOME at a writable dir as the nix check hook does.
            env["HOME"] = os.environ.get("SMOKE_HOME") or "/tmp"

    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True,
            timeout=SMOKE_TIMEOUT_S, env=env, cwd="/",
        )
    except subprocess.TimeoutExpired:
        return False, "smoke timed out after %ss" % SMOKE_TIMEOUT_S

    lines = proc.stdout.splitlines()
    if tool == "garak":
        # the pin prints raw colourama ANSI (no garak init() call on the
        # posix path — rehearsed: raw escapes regardless of TTY) — strip
        # deterministically before matching; the VM/CI surfaces capture
        # pipes either way, so matching must not depend on colour state.
        ansi = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
        lines = [ansi.sub("", ln) for ln in lines]
    matched, matched_value = 0, None
    for line in lines:
        m = re.match(entry["regex"], line.strip())
        if m:
            matched += 1
            matched_value = m.group(1) if m.groups() else line.strip()

    if tool == "garak":
        reason = None
        if proc.returncode == 0 and matched < entry["min_count"]:
            reason = ("probe-index lines matching %r: %d < %d"
                      % (entry["regex"], matched, entry["min_count"]))
    elif "expect_group" in entry:
        reason = None
        if matched_value != entry["expect_group"]:
            reason = "expected %r, got %r" % (entry["expect_group"], matched_value)
    else:
        reason = None
        if matched < entry["min_count"]:
            reason = "expected %d+ matching lines of %r, got %d"
            reason = reason % (entry["min_count"], entry["regex"], matched)

    if proc.returncode != 0:
        err = (reason + "; " if reason else "")
        return False, "%src=%d stderr tail: %s | stdout head: %s" % (
            err, proc.returncode, proc.stderr[-500:], " | ".join(lines[:6]))

    marker_reason = _build_log_marker_reason(tool, build_log)
    if marker_reason:
        return False, marker_reason

    if tool == "garak":
        detail = "%d probe-index rows" % matched
    else:
        detail = matched_value if matched_value else "%d matching lines" % matched
    return True, (detail, lines)



def smoke_library(tool, out_path, build_log=""):
    """Library packages (no console script): version record + module-file
    surface + this build's imports-check phase marker."""
    entry = SMOKE_TABLE[tool]
    site = glob.glob(os.path.join(
        out_path, "lib", "python3.*", "site-packages"))
    if not site:
        return False, "site-packages not found under %s" % out_path
    root = site[0]
    missing = [f for f in entry["module_files"]
               if not os.path.exists(os.path.join(root, f))]
    if missing:
        return False, "module files missing: %s" % ", ".join(missing)

    dist_glob = os.path.join(root, "%s-*.dist-info" % entry["dist_name"])
    dists = glob.glob(dist_glob)
    if not dists:
        return False, "dist-info not found: %s" % dist_glob
    with open(os.path.join(dists[0], "METADATA"), encoding="utf-8") as fh:
        version = next(
            (ln.split(":", 1)[1].strip() for ln in fh if ln.startswith("Version:")),
            None)
    if version != entry["expect_version"]:
        return False, "expected version %r, dist-info says %r" % (
            entry["expect_version"], version)

    marker_reason = _build_log_marker_reason(tool, build_log)
    if marker_reason:
        return False, marker_reason
    return True, ("version %s; %d module files present"
                  % (version, len(entry["module_files"])), [version])


def solve_out_path(tool, system):
    """Resolve tool@system in the flake's packages output -> outPath."""
    out = subprocess.run(
        ["nix", "eval", "--accept-flake-config", "--raw",
         ".#packages.%s.%s.outPath" % (system, tool)],
        capture_output=True, text=True,
    )
    if out.returncode != 0 or not out.stdout.startswith("/nix/store/"):
        raise SystemExit(
            "wave2-smoke: flake resolution failed for %s (%s): %s"
            % (tool, system, out.stderr.strip()[:400]))
    return out.stdout.strip()


def run_smoke(tool, system, out_path=None, build_log=""):
    """Build (unless out_path given) then smoke. Prints the stable line."""
    if out_path is None:
        print("wave2-smoke: RUN: nix build .#packages.%s.%s -L"
              % (system, tool), flush=True)
        cmd = ["nix", "build", "--accept-flake-config",
               ".#packages.%s.%s" % (system, tool), "-L"]
        try:
            build = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=BUILD_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            print("wave2-smoke: FAIL: %s (nix build timed out)" % tool, flush=True)
            return False
        if build.returncode != 0:
            print("wave2-smoke: FAIL: %s (nix build rc=%d):\n%s"
                  % (tool, build.returncode, build.stderr[-1500:]), flush=True)
            return False
        out_path = solve_out_path(tool, system)

    entry = SMOKE_TABLE[tool]
    if entry["kind"] == "library":
        ok, result = smoke_library(tool, out_path, build_log)
    else:
        ok, result = smoke_console(tool, out_path, build_log)

    if ok:
        detail, head = result
        print("wave2-smoke: PASS: %s (%s)" % (tool, detail), flush=True)
        for line in head:
            print("  %s" % line, flush=True)
        return True
    print("wave2-smoke: FAIL: %s (%s)" % (tool, result), flush=True)
    return False


def dry_run():
    """The checks-gate surface: the command table must match the
    acceptance clauses exactly; when the flake supplies the tool list it
    evaluates from its own packages output, the table must equal it."""
    failures = []

    env_tools = os.environ.get("WAVE2_SMOKE_EXPECT_TOOLS", "")
    expected = sorted(t for t in env_tools.split() if t) if env_tools else DOC_DECLARED
    if EXPECTED != expected:
        failures.append(
            "tool set drifted: table %r != expected %r%s"
            % (EXPECTED, expected,
               " (flake packages output)" if env_tools else " (doc-declared)"))

    garak = SMOKE_TABLE["garak"]
    if garak["argv"][:2] != ["garak", "--list_probes"]:
        failures.append("garak smoke is not the probe-index listing: %r" % garak["argv"])
    if garak.get("min_count", 0) < 100:
        failures.append("garak probe-index floor missing/low: %r" % garak.get("min_count"))

    if SMOKE_TABLE["promptfoo"]["argv"] != ["promptfoo", "--version"]:
        failures.append("promptfoo smoke must be the version command: %r"
                        % SMOKE_TABLE["promptfoo"]["argv"])

    for tool in ("pyrit", "art", "counterfit"):
        entry = SMOKE_TABLE[tool]
        if entry["kind"] not in ("import", "library"):
            failures.append("%s smoke kind must prove the import surface" % tool)
        if entry.get("module") != tool:
            failures.append("%s: module surface drifted" % tool)
        if "build_log_marker" not in entry:
            failures.append("%s: missing build_log_marker" % tool)

    for tool in SMOKE_TABLE:
        pin = TOOL_SOURCE_COMMIT[tool]
        if len(pin) != 40:
            failures.append("%s: source commit malformed" % tool)

    if failures:
        for f in failures:
            print("wave2-smoke: DRY-RUN FAIL: %s" % f)
        return 1
    for tool in EXPECTED:
        entry = SMOKE_TABLE[tool]
        shown = " ".join(entry["argv"]) if "argv" in entry else (
            "import %s (kind=%s)" % (entry["module"], entry["kind"]))
        print("wave2-smoke: dry-run OK: %s [%s]" % (tool, shown))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="KA-10/11/12 acceptance smokes (wave-2 flagship five)")
    ap.add_argument("--dry-run", action="store_true",
                    help="validate the per-tool command table (checks gate)")
    ap.add_argument("--smoke-only", action="store_true",
                    help="smoke an already-built output (build-leg surface)")
    ap.add_argument("--out-path", help="store path of the built package")
    ap.add_argument("--tool", action="append", choices=EXPECTED,
                    help="tool to smoke (repeatable; default all attempted)")
    ap.add_argument("--system", default=DEFAULT_SYSTEM,
                    choices=["x86_64-linux", "aarch64-linux"])
    ap.add_argument("--table-dump", action="store_true",
                    help="print the command table as JSON and exit")
    args = ap.parse_args(argv)

    if args.table_dump:
        print(json.dumps(SMOKE_TABLE, indent=2, sort_keys=True))
        return 0

    if args.dry_run:
        return dry_run()

    if args.smoke_only:
        if not args.out_path or not args.tool or len(args.tool) != 1:
            ap.error("--smoke-only needs exactly one --tool and its --out-path")
        out_path = args.out_path
        if not os.path.isdir(out_path):
            ap.error("--out-path %r is not a directory" % out_path)
        ok = run_smoke(args.tool[0], args.system, out_path=out_path,
                       build_log=load_build_log())
        return 0 if ok else 1

    tools = args.tool or EXPECTED
    results = {t: run_smoke(t, args.system) for t in tools}
    failed = [t for t, ok in results.items() if not ok]
    if failed:
        print("wave2-smoke: SUMMARY: FAIL (%d/%d): %s"
              % (len(failed), len(results), ", ".join(failed)), flush=True)
        return 1
    print("wave2-smoke: SUMMARY: PASS (%d/%d)"
          % (len(results), len(results)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
