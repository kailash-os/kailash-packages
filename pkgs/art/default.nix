# art — adversarial-robustness-toolbox (Trusted-AI/adversarial-robustness-toolbox; KA-12.1 #84).
# Shape 1 (interpreted-language tools, plan §5.3): buildPythonLibrary over
# the committed nvfetcher pin, doCheck = false (no framework tests in the
# build sandbox), pythonImportsCheck ["art", "art.attacks.evasion",
# "art.estimators.classification"] as the smoke gate. Recipe lineage: the
# garak exemplar (pkgs/garak/default.nix), rebuilt against the ART pin.
#
# Upstream truth at the pin (4da50bdc, main @ 2026-10-08, __version__
# 1.20.1): setup.py declares install_requires = numpy>=1.18.0, scipy>=1.4.1,
# scikit-learn>=0.22.2, six, setuptools, tqdm — the pure-python core. The
# framework sets (torch/tensorflow/keras/xgboost/lightgbm/…) are
# extras_require groups upstream and were read from the pinned tree; at
# import time the estimators/adversarial-patch modules that name those
# frameworks resolve them under `if TYPE_CHECKING:` or inside method
# bodies (verified per file on the pinned tree), so none is a build or
# import dependency. The framework extras stay documented opt-ins, never
# build inputs (the pyrit deps.nix scope rule — R2b, §5.3).
#
# Licence: MIT — read from the upstream LICENSE at the pin (plan §11.3
# carried "AGPL-class" unverified; this packaging corrects the record in
# the manifest entry and PR). Interpreter: python313 — the lock's
# default python3 is 3.14 and counterfit/a-5 sibling pinning keeps the
# A-5 research stack on one set (§5.3 one-package-set-per-tool).
{
  lib,
  callPackage,
  python313,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };
in

python313.pkgs.buildPythonPackage {
  pname = "art";
  # pin date from _sources.art.date
  version = "1.20.1-unstable-2026-10-08";

  src = sources.art.src;
  pyproject = true;

  build-system = with python313.pkgs; [ setuptools ];

  # the pinned setup.py install_requires list, resolved from the locked
  # nixpkgs python313Packages set; framework sets are upstream extras and
  # are deliberately NOT inputs (see header) — `import art` resolves
  # them lazily (verified on the pinned tree)
  dependencies = with python313.pkgs; [
    numpy
    scipy
    scikit-learn
    six
    tqdm
  ];

  doCheck = false;
  pythonImportsCheck = [
    "art"
    "art.attacks.evasion"
    "art.estimators.classification"
  ];

  meta = {
    description = "Adversarial Robustness Toolbox — attacks, defences, metrics and estimators for machine learning security (Evasion, Poisoning, Extraction, Inference)";
    homepage = "https://github.com/Trusted-AI/adversarial-robustness-toolbox";
    changelog = "https://github.com/Trusted-AI/adversarial-robustness-toolbox/commits/${sources.art.version}";
    license = lib.licenses.mit;
    # library surface: no console entry point, no mainProgram
  };
}
