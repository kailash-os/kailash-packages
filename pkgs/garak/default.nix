# garak — LLM vulnerability scanner (NVIDIA/garak; KA-10.1 #80).
# Shape 1 (interpreted-language tools, plan §5.3): buildPythonApplication
# over the committed nvfetcher pin, doCheck = false (VM tests cover
# behaviour at kailash-os#65) and pythonImportsCheck ["garak"] as the
# smoke gate. Recipe lineage: garak's own pyproject (flit_core backend,
# version 0.17.1.pre1 at the pin, requires-python >= 3.11) — nixpkgs
# has no garak recipe at the lock, so the dep list is maintained
# in-tree against the pinned pyproject and re-verified with every pin
# update (the pin-update PR carries the build status).
{
  lib,
  callPackage,
  python3,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };
in

python3.pkgs.buildPythonApplication {
  pname = "garak";
  # garak pyproject version + pin date from _sources.garak.date
  version = "0.17.1.pre1-unstable-2026-10-09";

  src = sources.garak.src;
  pyproject = true;

  doCheck = false;
  doInstallCheck = true;
  # the smoke gate (issue #80): `import garak` pulls _config + _plugins,
  # i.e. yaml, xdg-base-dirs + the garak package itself — nothing
  # heavier: every model/encoding dep is function-scope (lazy) in the
  # pinned tree
  pythonImportsCheck = [ "garak" ];

  build-system = with python3.pkgs; [ flit-core ];

  # the pinned pyproject dependencies list, resolved from
  # nixpkgs-locked python3Packages; version-capped pins that fight the
  # lock are widened via pythonRelaxDeps (below) so the runtime link is
  # the nixpkgs-locked derivation
  dependencies = with python3.pkgs; [
    transformers
    datasets
    colorama
    tqdm
    cohere
    google-api-python-client
    backoff
    nltk
    accelerate
    avidtools
    stdlibs
    langchain
    torch
    sentencepiece
    markdown
    numpy
    zalgolib
    ecoji
    litellm
    llm
    jsonpath-ng
    huggingface-hub
    python-magic
    xdg-base-dirs
    ollama
    google-cloud-translate
    grpcio-tools
    langdetect
    tiktoken
    mistralai
    pillow
    ftfy
    websockets
    boto3
    py-markdown-table
  ];

  # pins in garak's pyproject that the nixpkgs-locked python set cannot
  # satisfy exactly (garak ==-pins, nixpkgs-locked ships newer):
  #   anthropic  ==0.40.0,<1.0.0  → lock has 1.6.0
  #   cmd2       ==2.4.3          → lock has 3.5.1
  #   deepl      ==1.17.0         → lock has 1.32.0
  #   avidtools  ==0.1.2          → lock has 0.2.1
  #   wn         ==0.9.5          → lock has 0.14.0
  #   langdetect ==1.0.9          → lock has 1.0.9 (kept; not relaxed)
  #   mistralai  ==1.5.2          → lock has 2.10.1
  #   datasets   >=3.0,<4.0        → lock has 4.5.0
  # pythonRelaxDeps strips the version spec from the metadata so these
  # runtime links resolve; the nixpkgs-locked versions above are what
  # ships, and each is re-checked against the pyproject at pin updates
  pythonRelaxDeps = [
    "anthropic"
    "cmd2"
    "deepl"
    "avidtools"
    "wn"
    "mistralai"
    "datasets"
  ];

  # pyproject pins with no nixpkgs-locked recipe; all three import only
  # inside functions at probe/runtime time (verified in the pinned
  # tree), never at `import garak`:
  #   mikeshardmind-base2048 → garak/probes/encoding.py:465 (probe init)
  #   ecoji-adjacent lorem   → garak/generators/test.py:8 (module) but
  #                            only reachable via the `test` generator
  #                            plugin, not the imports check
  #   nvidia-riva-client     → garak/langproviders/remote.py:65 (Riva
  #                            translator init)
  # NOTE: ecoji IS in nixpkgs and IS kept; only these three are removed
  pythonRemoveDeps = [
    "mikeshardmind-base2048"
    "lorem"
    "nvidia-riva-client"
  ];

  # flit builds need the version/module; garak ships pyproject-based
  # flit config — nothing else required at build time

  passthru.updateScript = [ ];

  meta = {
    description = "LLM vulnerability scanner (probes, detectors, buffs and harnesses)";
    homepage = "https://github.com/NVIDIA/garak";
    changelog = "https://github.com/NVIDIA/garak/commits/${sources.garak.version}";
    license = lib.licenses.asl20;
    mainProgram = "garak";
  };
}
