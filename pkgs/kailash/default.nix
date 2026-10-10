# kailash — pinned to THIS repository's cli subtree (KA-14.1).
#
# The CLI core is a first-party package (plan §7.1: "packaged in the
# packages repo"), not an upstream pin: the source is the manifest-aware
# cli/ directory at the repo root — the same tree the flake's checks
# exercise — so the derivation carries the loader + commands exactly as
# reviewed, and the manifest files beside cli/ resolve through the
# loader's __file__-relative paths in the checked-out tree (KA-14.2 adds
# the §7.3 wrapProgram store-baking of those paths).
{
  lib,
  python3Packages,
}:

python3Packages.buildPythonApplication {
  pname = "kailash";
  version = "0.1.0";
  pyproject = true;

  # the tool dir at the repo root (cli/), consumed wholesale — pyproject,
  # the kailash package, and the checker script ride together
  src = ../../cli;

  build-system = with python3Packages; [ setuptools ];

  # declared the way the validator check env declares pyyaml
  # (checks.manifest-wellformed: python3.withPackages (ps: [ ps.pyyaml ])):
  dependencies = with python3Packages; [ pyyaml ];

  pythonImportsCheck = [ "kailash" "kailash.manifest" "kailash.cli" ];

  # CLI is import-clean under the sandbox; there is no test suite in the
  # wheel (the behavioural gate is checks.kailash-cli-self-test, which
  # exercises list/search/info against the real manifest)
  doCheck = false;

  meta = {
    description = "Kailash OS manifest CLI - list/search/info over the tool manifest";
    license = lib.licenses.bsd3;
    mainProgram = "kailash";
  };
}
