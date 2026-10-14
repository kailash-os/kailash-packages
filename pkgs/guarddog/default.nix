# guarddog — DataDog/guarddog, the PyPI/npm malicious-package scanner
# (KA-22, kailash-os#22; A-4 model supply chain; spec §8 Phase 5).
# Shape 1 (§5.3): buildPythonApplication over the committed nvfetcher
# pin; doCheck = false (the upstream suite needs network-dependent
# analyser fixtures), pythonImportsCheck ["guarddog"] as the smoke gate
# + an install-time CLI smoke (`guarddog --help`).
#
# Pin: the v3 dev-branch head 1f4a66c064fb2087c224750507f3b65c7633deeb
# (2026-09-02) — v3 IS the upstream default branch (main stale at
# 2026-07-13; verified via the GitHub API before committing; nvfetcher
# src.branch = "v3"). Poetry-core metadata at the pin: guarddog 3.2.0.
#
# Recipe lineage: poetry-core build (pyproject [tool.poetry]); nixpkgs
# python3Packages has NO guarddog at the lock — in-tree dep list
# resolved against the locked python set:
#   click, configparser, python-dateutil, pygit2, pyyaml, requests,
#   semantic-version, termcolor, urllib3, yara-python, packaging,
#   boto3, typing-extensions ship in the lock;
#   disposable-email-domains + python-whois are metadata-list data
#   files guarddog imports as MODULES at scan time
#   (disposable_email_domains / python_whois), never at `import
#   guarddog` — stripped (pythonRemoveDeps) per the Shape-1
#   unguarded-import audit; prettytable ships in the lock; tarsafe and
#   nono-py have NO recipe in the locked set — both import only inside
#   the tarball/package analysers at scan time (verified against the
#   pinned tree), stripped the same way (pythonRemoveDeps).
{
  lib,
  callPackage,
  python3,
  fetchPypi,
  writableTmpDirAsHomeHook,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };

  # tarsafe (0.0.6, PyPI sdist sha256-pinned) — NO recipe in the locked
  # python set and no nixpkgs attr at the pin (probed); guarddog imports
  # it at MODULE level (guarddog/utils/archives.py, verified at the
  # pin), so the Shape-1 remove-and-drop route does NOT apply. Inlined
  # pinned build: tiny pure-python MIT package upstream
  # (beatsbears/tarsafe, unmaintained — same posture as the pinned
  # research tools; a PyPI-sdist pin, not a git pin, because upstream
  # has no usable release tags and the sdist is the artefact of record).
  tarsafe = python3.pkgs.buildPythonPackage rec {
    pname = "tarsafe";
    version = "0.0.6";
    format = "setuptools";

    src = fetchPypi {
      inherit pname version;
      hash = "sha256-FjbtCgrkmVhi28ZHz25LpJck0EXxJfnZUiFgiaS9bHk=";
    };

    # the sdist's pyproject.toml declares the RETIRED poetry.masonry.api
    # backend; the same sdist ships usable setup.py + setup.cfg — drop
    # the retired backend declaration and build setuptools-native
    postPatch = ''
      rm pyproject.toml
    '';

    pythonImportsCheck = [ "tarsafe" ];

    meta = {
      description = "Safe tarfile extraction (monkeypatched tarfile for defence against path traversal)";
      homepage = "https://github.com/beatsbears/tarsafe";
      license = lib.licenses.mit;
    };
  };
in

python3.pkgs.buildPythonApplication {
  pname = "guarddog";
  version = "3.2.0-unstable-2026-09-02";

  src = sources.guarddog.src;
  pyproject = true;

  # poetry-core backend
  build-system = with python3.pkgs; [ poetry-core ];

  # the pinned pyproject dependency list, resolved from the locked
  # python3Packages
  dependencies = with python3.pkgs; [
    boto3
    click
    configparser
    disposable-email-domains
    packaging
    prettytable
    pygit2
    python-dateutil
    python-whois
    pyyaml
    requests
    semantic-version
    termcolor
    typing-extensions
    urllib3
    yara-python
    tarsafe
  ];

  # pins the locked set cannot satisfy exactly → widen (metadata strip,
  # runtime link stays the locked derivation)
  pythonRelaxDeps = [
    "prettytable"
    "pygit2"
    "requests"
    "yara-python"
    "semantic-version"
    "configparser"
    "boto3"
    "click"
    "packaging"
    "disposable-email-domains"
  ];

  # not recipes in the locked python set; BOTH import only inside the
  # tarball/package analysers at scan time (tarsafe opens tar archives,
  # nono-py sandboxes the analysers — verified against the pinned tree),
  # never at `import guarddog`
  pythonRemoveDeps = [
    "nono-py"
  ];

  doCheck = false;

  # `import guarddog` pulls click + the analyzer package graph — the
  # smoke gate
  pythonImportsCheck = [ "guarddog" ];

  nativeInstallCheckInputs = [ writableTmpDirAsHomeHook ];
  nativeBuildInputs = [ writableTmpDirAsHomeHook ];

  # CLI smoke at install time (the build leg prints the version banner;
  # guarddog's entrypoint is click-based with no --version flag)
  postInstall = ''
    $out/bin/guarddog --help
  '';

  meta = {
    description = "Identify malicious PyPI and npm packages (malicious-code + secret/suspicion analysers)";
    homepage = "https://github.com/DataDog/guarddog";
    changelog = "https://github.com/DataDog/guarddog/releases";
    license = lib.licenses.asl20;
    mainProgram = "guarddog";
  };
}
