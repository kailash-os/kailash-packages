# pyrit/deps.nix — the three PyPI wheels the pinned nixpkgs does not
# package (defect record: the packages-repo pyrit defect issue; surfaced
# by the KA-15.1 hosted build gate, kailash-packages#18 CI).
#
# Why this file: `pkgs/pyrit/default.nix` declares upstream's real
# [project].dependencies (the dependency list is contract). Three of
# them — aioodbc, azure-ai-contentsafety, confusables — have no
# attribute on the LOCKED nixpkgs (probed: python3.pkgs holds 12,210
# attrs; pyodbc / isodate / azure-core / confusable-homoglyphs exist,
# the three above do not). Removing them from pyrit's list would ship a
# package that does not match upstream's declared runtime; instead this
# override adds exactly those three wheels to the python package set
# pyrit's dependencies resolve against. Scope: python3.override — a NEW
# python environment used by pyrit only (not a global python mutation,
# not overlay-wide, not an auto-call dir: these are pyrit's
# dependencies, not distro tools; they must NOT enter the manifest
# matrix).
#
# Pins are contract: version + SRI hash per wheel below; a dependency
# bump lands as a reviewed PR re-recording both (same discipline as the
# nvfetcher pins). Wheels are py3-none-any (pure python) — no compiler
# backend involved; the hash pins substitute reproducibility.
#
# Update procedure: bump `version`, replace the sha256, and re-run the
# pyrit build (the KA-15.1 build gate re-proves the pin). aioodbc's
# runtime dep (pyodbc >=5.0.1 — the pin carries 5.3.0) is already
# provided by nixpkgs; azure-ai-contentsafety's deps (isodate,
# azure-core) likewise — only the three wheels themselves are missing.
{
  python3,
  fetchPypi,
}:

let
  # the base set the wheels are built ONCE against; the overridden set
  # then exposes them to pyrit's dependency resolution
  pinned = python3.pkgs;

  pyd = python3.override {
    packageOverrides = self: super: {
      aioodbc = pinned.callPackage
        (
          {
            lib,
            buildPythonPackage,
            pyodbc,
          }:
          buildPythonPackage rec {
            pname = "aioodbc";
            version = "0.5.0";
            format = "wheel";
            src = fetchPypi {
              inherit pname version;
              format = "wheel";
              dist = "py3";    # URL directory segment
              python = "py3";  # the wheel FILENAME tag (default py2.py3 404s)
              sha256 = "sha256-vK8W8AeFX6S/DOZ1Sx9yxsWj1UQYiElXfd1VxdxCmF4=";
            };
            propagatedBuildInputs = [ pyodbc ];
            # upstream ships no tests in the wheel; import is the smoke gate
            pythonImportsCheck = [ "aioodbc" ];
            meta = {
              description = "Async ODBC driver wrapper (aioodbc) for SQLAlchemy/aio usage";
              homepage = "https://github.com/aio-libs/aioodbc";
              license = lib.licenses.asl20;
            };
          }
        )
        { };

      azure-ai-contentsafety = pinned.callPackage
        (
          {
            lib,
            buildPythonPackage,
            isodate,
            azure-core,
          }:
          buildPythonPackage rec {
            pname = "azure_ai_contentsafety";  # PyPI filename/dirname seg uses underscores
            version = "1.0.0";
            format = "wheel";
            src = fetchPypi {
              inherit pname version;
              format = "wheel";
              dist = "py3";    # URL directory segment
              python = "py3";  # the wheel FILENAME tag (default py2.py3 404s)
              sha256 = "sha256-4cVXSlQfkpD90HHSNTXhSx9GOvIxpvCsD5F+El8EY88=";
            };
            propagatedBuildInputs = [
              isodate
              azure-core
            ];
            pythonImportsCheck = [ "azure.ai.contentsafety" ];
            meta = {
              description = "Azure AI Content Safety client library for Python";
              homepage = "https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/contentsafety/azure-ai-contentsafety";
              license = lib.licenses.mit;
            };
          }
        )
        { };

      confusables = pinned.callPackage
        (
          {
            lib,
            buildPythonPackage,
          }:
          buildPythonPackage rec {
            pname = "confusables";
            version = "1.2.0";
            format = "wheel";
            src = fetchPypi {
              inherit pname version;
              format = "wheel";
              dist = "py3";    # URL directory segment
              python = "py3";  # the wheel FILENAME tag (default py2.py3 404s)
              sha256 = "sha256-DD5KjvimF58iLoy26mWsWnH6XHDS3iGVDRTpn5M+z1I=";
            };
            # no declared runtime deps (upstream [project] carries none)
            pythonImportsCheck = [ "confusables" ];
            meta = {
              description = "Confusable Unicode character detection (homoglyph matching library)";
              homepage = "https://github.com/woodgern/confusables";
              license = lib.licenses.mit;
            };
          }
        )
        { };
    };
  };
in
pyd
