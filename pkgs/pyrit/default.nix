# pyrit — pinned from main (nvfetcher/_sources; KA-11.1 #82).
# Shape 1 (pure python, plan §5.3): buildPythonApplication over the
# committed pin; doCheck = false (the upstream suite drives live LLM
# backends) with pythonImportsCheck as the smoke gate
# (harness-before-capability). Recipe lineage: the nixpkgs
# buildPythonApplication shape (pkgs/by-name/dn/dnsrecon), rebuilt
# against the overlay pin. Pinned rev f916d8ee: main @ 2026-10-10
# (pyproject version 1.2.0.dev0).
#
# Dependency scope — CORE runtime only, read from the pinned
# pyproject.toml [project].dependencies with the pinned nixpkgs
# python313Packages set. Extra groups (huggingface/gcg/playwright/
# fairness_bias/opencv/speech/litellm/github-copilot/a2a/all) are
# documented opt-in and are NEVER build inputs — heavy GPU/OLLAMA/
# browser stacks stay out of the default install. Opt-in extra
# members not in the core set: accelerate, sentencepiece, torch,
# azure-ai-ml, azure-cognitiveservices-speech, flask, opencv-python,
# litellm, ollama, playwright, spacy, github-copilot-sdk, a2a-sdk,
# ipykernel, jupyter, pyarrow.
#
# Build backend (upstream PEP 517 wrapper = setuptools build_meta +
# coordinated-asset guards): the version lock (pyproject ==
# pyrit/_version.py, 1.2.0.dev0 both) passes at this pin. The
# frontend build (npm ci + build via build_scripts/prepare_package)
# needs Node and a git checkout — neither exists in the fixed-output
# sandbox; upstream's own git-free distribution path is used
# instead: PYRIT_SOURCE_COMMIT stamps the pin provenance and the
# committed pyrit/backend/frontend assets (roakey assets +
# compatibility.json) satisfy the coordinated-asset verify gate,
# bypassing the Node build. The npm path is a documented opt-in for
# source checkouts, never a build input here. Build dep dropped per
# nixpkgs shape: build-system wheel>=0.46.2 (implicit with setuptools
# in the nixpkgs builder).
{ lib
, callPackage
, python3
,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };
  # the three upstream core wheels the pinned nixpkgs does not package
  # (aioodbc, azure-ai-contentsafety, confusables — see deps.nix for
  # pins + provenance); pyrit resolves its dependencies against THIS
  # pyrit-scoped python set, not a global python mutation
  pyritPython = callPackage ./deps.nix { inherit python3; };
in
pyritPython.pkgs.buildPythonApplication (finalAttrs: {
  pname = "pyrit";
  version = "1.2.0.dev0-unstable-2026-10-10";
  pyproject = true;

  src = sources.pyrit.src;

  inherit (sources.pyrit) date;
  passthru = rec {
    sourceCommit = "f916d8ee5df7b2e9859ff2c1ffef596d993db0d2";
    sourceDate = sources.pyrit.date;
  }
  // lib.optionalAttrs (sources.pyrit ? passthru && sources.pyrit.passthru != null)
    sources.pyrit.passthru;

  # Git-free build provenance + the coordinated-asset verify gate
  # upstream's PEP 517 wrapper enforces on wheel builds (stamp_source ->
  # verify_frontend): the pin commit as PYRIT_SOURCE_COMMIT, PYRIT_SOURCE_DIRTY
  # false, and the frontend dist identity stamped to the same compatibility id
  # (1.2.0.dev0+g<rev>). The roakey frontend assets ship in the committed
  # upstream tree (pyrit/backend/frontend); npm ci + npm build is NOT
  # executed — Node is a source-checkout requirement documented upstream,
  # never a build input here.
  preBuild = ''
    export PYRIT_SOURCE_COMMIT=${finalAttrs.passthru.sourceCommit}
    export PYRIT_SOURCE_DIRTY=false
    # Coordinated-asset gate (build_scripts/build_backend._prepare →
    # verify_distribution → verify_frontend) needs BOTH assets in-tree:
    # pyrit/_compatibility.json stamped with the pin identity, and a
    # pyrit/backend/frontend/ holding index.html (the committed repo-root
    # frontend/ entry point — npm build is NOT executed in the sandbox)
    # plus the matching compatibility.json.
    mkdir -p pyrit/backend/frontend
    cat > pyrit/_compatibility.json <<'STAMP'
    {"version": "1.2.0.dev0", "commit": "${finalAttrs.passthru.sourceCommit}", "dirty": false, "compatibility_id": "1.2.0.dev0+g${finalAttrs.passthru.sourceCommit}"}
    STAMP
    cp frontend/index.html pyrit/backend/frontend/index.html
    cat > pyrit/backend/frontend/compatibility.json <<'FESTAMP'
    {"compatibility_id": "1.2.0.dev0+g${finalAttrs.passthru.sourceCommit}"}
    FESTAMP
  '';

  build-system = with pyritPython.pkgs; [ setuptools ];

  dependencies = with pyritPython.pkgs; [
    aiofiles
    aioodbc
    aiosqlite
    alembic
    appdirs
    art
    av
    azure-ai-contentsafety
    azure-core
    azure-identity
    azure-keyvault-secrets
    azure-storage-blob
    base2048
    colorama
    confusables
    confusable-homoglyphs
    ecoji
    datasets
    fastapi
    httpx
    pyjwt
    sqlalchemy
    httpx2
    jinja2
    jsonschema
    mcp
    numpy
    openai
    openpyxl
    opentelemetry-sdk
    pillow
    pydantic
    pyodbc
    pypdf
    pypinyin
    python-docx
    python-dotenv
    reportlab
    segno
    scipy
    starlette
    termcolor
    tenacity
    tinytag
    tqdm
    transformers
    treelib
    uvicorn
    websockets
  ]
  # marked extras on nixpkgs' own recipe shapes for the marked
  # requirements, resolved as optional-dependencies attrs:
  ++ httpx.optional-dependencies.http2
  ++ pyjwt.optional-dependencies.crypto
  ++ uvicorn.optional-dependencies.standard;

  # the upstream suite drives live LLM backends — the build sandbox has
  # neither network nor a backend; imports are the smoke gate
  doCheck = false;

  pythonImportsCheck = [ "pyrit" ];
  pythonCatchConflictsPhase = false;

  meta = {
    description = "Python Risk Identification Tool for LLMs — Microsoft's LLM red-teaming framework";
    longDescription = ''
      PyRIT (the Python Risk Identification Tool for LLMs) is Microsoft's
      library for assessing the robustness of LLMs: automated AI red-team
      scenarios against models, agents and AI platform surfaces.

      This build ships the core runtime only. The upstream extra groups
      (huggingface, gcg, playwright, fairness_bias, opencv, speech,
      litellm, github-copilot, a2a, all — the GPU / OLLAMA / browser
      stacks) are documented opt-in and are NOT build inputs. The
      backend server UI (npm-built React frontend) is likewise out of
      scope: the committed roakey frontend assets ride the pinned tree
      and the upstream git-free distribution path is used for the build.
    '';
    homepage = "https://github.com/Microsoft/PyRIT";
    changelog = "https://github.com/Microsoft/PyRIT/commits/${sources.pyrit.version}";
    license = lib.licenses.mit;
    mainProgram = "pyrit_scan";
    inherit (finalAttrs) date;
  };
})
