# kailash — pinned to THIS repository's cli subtree (KA-14.1/KA-14.2).
#
# The CLI core is a first-party package (spec §6.1: "packaged in the
# packages repo"), not an upstream pin: the source is the manifest-aware
# cli/ directory at the repo root — the same tree the flake's checks
# exercise — so the derivation carries the loader + commands exactly as
# reviewed.
#
# §7.3 the manifest-baked path (the drift killer): the two manifest
# files are derivation INPUTS and the wrapper bakes their store paths
# into the binary's environment —
#   KAILASH_MANIFEST    -> the store path of manifest/tools.yaml
#   KAILASH_CATEGORIES  -> the store path of manifest/categories.yaml
# — so the CLI's derivation hash changes whenever the manifest content
# changes and `kailash list` can never disagree with the installed
# system. The env contract is per-file (cli/kailash/manifest.py): each
# variable names the FILE, the two are read independently.
{
  lib,
  python3Packages,
  makeBinaryWrapper,
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

  # §7.3: the two manifest files as derivation inputs — their store
  # paths go into the wrapper env below, their content into this
  # derivation's hash
  manifestTools = ../../manifest/tools.yaml;
  manifestCategories = ../../manifest/categories.yaml;

  nativeBuildInputs = [ makeBinaryWrapper ];

  pythonImportsCheck = [ "kailash" "kailash.manifest" "kailash.cli" ];

  # CLI is import-clean under the sandbox; there is no test suite in the
  # wheel (the behavioural gate is checks.kailash-cli-self-test, which
  # exercises list/search/info against the real manifest; the env-bake
  # contract the wrapper implements is asserted there per-file)
  doCheck = false;

  # §7.3 the drift killer: bake the manifest store paths into the
  # binary env. `--prefix` : form — a colon-separated list whose sole
  # entry is the store path (the env contract is a single file path;
  # the prefix form keeps the assignment visible/patchable and
  # whitespace-proof against store-path quirks).
  postFixup = ''
    wrapProgram $out/bin/kailash \
      --prefix KAILASH_MANIFEST : $manifestTools \
      --prefix KAILASH_CATEGORIES : $manifestCategories
  '';

  meta = {
    description = "Kailash OS manifest CLI - list/search/info over the tool manifest";
    license = lib.licenses.bsd3;
    mainProgram = "kailash";
  };
}
