# counterfit — Azure/counterfit, the A-5 model-attack CLI (KA-12.2 #85).
# Shape 1 (interpreted-language tools, plan §5.3) on the garak exemplar:
# buildPythonApplication over the committed nvfetcher pin, doCheck = false
# (VM tests cover behaviour at kailash-os#65), pythonImportsCheck as the
# smoke gate.
#
# REFERENCE POSTURE (no freshness claim): upstream is dormant — main tip
# c00edbf5 is the 2025-07-18 maintainer-list update; the repo moved from
# secureworks/counterfit (404 at the plan-time owner name) to
# Azure/counterfit. Pinned to the exact main head at pin time (R7):
# version records upstream 1.1.0 + the pin date. Pins are contract.
#
# Recipe lineage: the pinned setup.py (setuptools, version 1.1.0 from
# `counterfit/__init__.py`, install_requires read from requirements.txt
# at build time — the requirements list IS the declared dependency
# surface at this pin). The dependency list below is that list resolved
# against the locked python313Packages, with named, anchored reductions
# (each traced on the pinned tree — zero import sites in the shipped
# package surface `counterfit/` + the console entry point):
#
#   - bs4, flask, hyperopt, questionary, traitlets — zero import sites
#     (the flask/fastapi demo servers live under examples/app, excluded
#     upstream; traitlets is a "Required for Windows" declare).
#   - pytorch_lightning, torchfile, tensorflow-hub, tensorflow-text —
#     zero import sites; the latter two are the requirements' own
#     textattack-scoped declares and the textattack framework wrapper
#     rides the anchored strip below. torchfile's declare ("To run
#     fga_jia_2019 attack") has no code path in the tree.
#   - cmd2-ext-test, pytest, coverage, pre-commit — repo tooling deps
#     (zero import sites), not runtime links. The cmd2 terminal dep is
#     kept.
#   - python-Levenshtein-wheels==0.13.2 — the deprecated wheel shim of
#     the `Levenshtein` distribution (its comment: pinned to dodge a
#     2021 >=0.20 breakage, since fixed); carried as nixpkgs
#     `levenshtein` (module `import Levenshtein` — the actual import
#     site in counterfit/reporting/text.py).
#   - augly: extras_require upstream AND imported at module top level
#     (counterfit/frameworks/__init__.py). No locked recipe exists and
#     the whole framework is one import line — it rides the anchored
#     strip (the augly attack configs stay listed by the scanner,
#     marked unavailable exactly as upstream degrades optional
#     frameworks).
#
# The strip is anchored: every rewritten string is asserted before
# rewriting, so a pin update that moves these lines fails the build
# loudly instead of silently diverging (pin-update PRs re-verify).
#
# Upstream console-script repair (kept, documented): this pin's
# setup.py declares entry_points counterfit=examples.terminal.terminal:main
# while excluding `examples` from find_namespace_packages — the
# installed `counterfit` command is BROKEN upstream at this pin. The
# packaging below ships the terminal as `counterfit.terminal` (copied
# in postPatch, `examples.terminal.` imports rewritten to relative) and
# repoints the entry point, so `counterfit` invokes the terminal the
# way upstream's docs describe. pythonImportsCheck also imports the
# console module.
#
# The art coupling: counterfit/frameworks/art/art.py imports
# `from art.utils import ...` at module top level, so the A-5 sibling
# derivation (pkgs/art, KA-12.1 #84) is a real dependency. Merge order
# KA-12.1 → KA-12.2.
{
  lib,
  callPackage,
  python313,
  writableTmpDirAsHomeHook,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };
  art = callPackage ../art { };
in

python313.pkgs.buildPythonApplication (finalAttrs: {
  pname = "counterfit";
  # upstream setup.py version + pin date from _sources.counterfit.date
  version = "1.1.0-unstable-2025-07-18";

  src = sources.counterfit.src;
  pyproject = true;

  build-system = with python313.pkgs; [ setuptools ];

  # NOTE on `art`: the overlay's ART derivation (outer let binding), NOT
  # python313Packages.art — the ASCII-art PyPI package of the same name
  # exists on the locked set (pyrit carries it for terminal banners), so
  # `art` must be referenced OUTSIDE the `with` block to bind to the
  # A-5 sibling derivation.
  dependencies =
    [
      art
    ]
    ++ (
      with python313.pkgs;
      [
        azure-storage-blob
        cmd2
    gym
    h5py
    levenshtein
    lightgbm
    matplotlib
    numpy
    onnxruntime
    optuna
    orjson
    pillow
    protobuf
    pygame
    pyglet
    pyyaml
    requests
    rich
    scipy
    tensorflow
    torchvision
    ]
    );

  # upstream ==-pins the 2021-era versions of nearly every line and the
  # locked set ships newer; the metadata specs are relaxed so these
  # runtime links resolve to the nixpkgs-locked derivations. numpy
  # (>=1.18.5), gym (>=0.26.0) and protobuf (>=3.9) are range-compatible
  # at the lock — not relaxed. Re-verified at every pin update.
  pythonRelaxDeps = [
    "azure-storage-blob"
    "cmd2"
    "h5py"
    "Levenshtein"
    "lightgbm"
    "matplotlib"
    "onnxruntime"
    "optuna"
    "orjson"
    "Pillow"
    "pygame"
    "pyglet"
    "PyYAML"
    "requests"
    "rich"
    "scipy"
    "tensorflow"
    "torchvision"
  ];

  postPatch = ''
    # The requirements.txt is the metadata's install_requires source at
    # build time: rewrite it to exactly the kept set declared above
    # (reductions named and evidenced in the header comment).
    cat > requirements.txt <<'REQS'
    azure-storage-blob
    cmd2
    gym
    h5py
    Levenshtein
    lightgbm
    matplotlib
    numpy
    onnxruntime
    optuna
    orjson
    Pillow
    protobuf
    pygame
    pyglet
    PyYAML
    requests
    rich
    scipy
    tensorflow
    torchvision
    REQS

    python3 - <<'PYEOF'
    import pathlib

    # Anchored strip: the textattack library import sites in the
    # framework wrapper (no locked recipe; optional framework upstream —
    # the wrapper degrades to None exactly as the scanner degrades the
    # framework).
    p = pathlib.Path("counterfit/frameworks/textattack/textattack.py")
    s = p.read_text()
    old = "from textattack import Attacker\nfrom textattack.datasets import Dataset\n"
    new = (
        "try:\n"
        "    from textattack import Attacker\n"
        "except ImportError:\n"
        "    Attacker = None\n"
        "try:\n"
        "    from textattack.datasets import Dataset\n"
        "except ImportError:\n"
        "    Dataset = None\n"
    )
    if old not in s:
        raise SystemExit("anchored strip 1 moved at this pin: " + str(p))
    p.write_text(s.replace(old, new, 1))

    # Anchored strip: the framework loader imports the augly + textattack
    # wrappers at module top level.
    p2 = pathlib.Path("counterfit/frameworks/__init__.py")
    s2 = p2.read_text()
    old2 = "from .art import art\nfrom .augly import augly\nfrom .textattack import textattack\n"
    new2 = (
        "from .art import art\n"
        "try:\n"
        "    from .augly import augly\n"
        "except ImportError:\n"
        "    augly = None\n"
        "try:\n"
        "    from .textattack import textattack\n"
        "except ImportError:\n"
        "    textattack = None\n"
    )
    if old2 not in s2:
        raise SystemExit("anchored strip 2 moved at this pin: " + str(p2))
    p2.write_text(s2.replace(old2, new2, 1))
    PYEOF

    # Console-script repair (see header): ship the terminal as
    # counterfit.terminal and repoint the entry point. One rewrite rule:
    # every `examples.terminal` reference (from-imports and absolute
    # module imports in the commands/__init__ registry) becomes
    # counterfit.terminal — the shipped package's absolute paths.
    cp -r examples/terminal counterfit/terminal
    find counterfit/terminal -name '*.py' -exec sed -i \
      -e 's/examples\.terminal/counterfit.terminal/g' {} +
    sed -i 's/counterfit=examples\.terminal\.terminal:main/counterfit=counterfit.terminal.terminal:main/' setup.py
  '';

  # `import counterfit` pulls the whole shipped surface: targets' sample
  # packs (torch, tensorflow, gym, matplotlib at module top level), the
  # frameworks init (art wrapper — real dep above), and the reporting
  # surface (azure.storage.blob, rich, Levenshtein). The console module
  # is proven importable too (the upstream repair above). cmd2 and
  # matplotlib want writable HOME when initialized; the hook redirects
  # HOME for the imports check (garak recipe precedent).
  doCheck = false;
  doInstallCheck = true;
  nativeInstallCheckInputs = [ writableTmpDirAsHomeHook ];
  nativeBuildInputs = [ writableTmpDirAsHomeHook ];
  pythonImportsCheck = [
    "counterfit"
    "counterfit.terminal.terminal"
  ];

  passthru = {
    inherit (sources.counterfit) date;
    sourceCommit = sources.counterfit.version;
  };

  meta = {
    description = "Counterfit — a CLI that provides a generic automation layer for assessing the security of ML models";
    homepage = "https://github.com/Azure/counterfit";
    changelog = "https://github.com/Azure/counterfit/commits/${sources.counterfit.version}";
    license = lib.licenses.mit;
    mainProgram = "counterfit";
  };
})
