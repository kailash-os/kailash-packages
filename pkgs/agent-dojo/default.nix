# agent-dojo — ETH's prompt-injection attack/defence evaluation
# environment for LLM agents (KA-22, kailash-os#22; A-3 agentic/MCP
# tool-use; plan §9 Phase 5). Shape 1 (§5.3): buildPythonApplication
# over the committed nvfetcher pin; hatchling backend (pyproject at the
# pin); doCheck = false (the upstream suite needs live LLM endpoints),
# pythonImportsCheck ["agentdojo"] as the smoke gate.
#
# NAME MAPPING (verified at the pin): the PyPI/package name is
# "agentdojo" (no hyphen); the manifest id keeps the census spelling
# agent-dojo — pname keeps the upstream dist name, meta.mainProgram +
# the manifest's nixos_menu exec carry the census spelling for the OS
# surfaces (the menu generator and CLI join on nixos_menu, never the
# pname).
#
# Pin: main head 089ed468cf3ed0322acc66b0211f26d9d90dbf60 (2026-06-02,
# verified via the GitHub API before committing). agentdojo 0.1.35 at
# the pin. MIT.
#
# Deps (pinned pyproject at the pin): openai, pydantic[email],
# docstring-parser, tenacity, langchain, typing-extensions, anthropic,
# cohere, pyyaml, click, deepdiff, rich, python-dotenv,
# google-genai — every one is a recipe in the locked python set at this
# pin (probed 8c3ced; the [email] extra on pydantic rides the locked
# email extras). Version caps relaxed to the locked set; the transformers/torch
# extra is NOT installed (optional upstream extra — probe-only surface).
{
  lib,
  callPackage,
  python3,
  writableTmpDirAsHomeHook,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };
in

python3.pkgs.buildPythonApplication {
  pname = "agentdojo";
  # pyproject version at the pin + pin date from _sources.agent-dojo.date
  version = "0.1.35-unstable-2026-06-02";

  src = sources.agent-dojo.src;
  pyproject = true;

  doCheck = false;

  build-system = with python3.pkgs; [ hatchling ];

  dependencies = with python3.pkgs; [
    anthropic
    click
    cohere
    deepdiff
    docstring-parser
    google-genai
    langchain
    openai
    python-dotenv
    pydantic
    pyyaml
    rich
    tenacity
    typing-extensions
  ];

  # upstream >=-pins vs the locked set → widen; runtime links stay the
  # locked derivations
  pythonRelaxDeps = [
    "langchain"
    "anthropic"
    "cohere"
    "openai"
    "pydantic"
    "deepdiff"
    "google-genai"
  ];

  pythonImportsCheck = [ "agentdojo" ];

  nativeInstallCheckInputs = [ writableTmpDirAsHomeHook ];
  nativeBuildInputs = [ writableTmpDirAsHomeHook ];

  # Upstream ships NO console script (pyproject [project.scripts]
  # absent at the pin — the benchmark drives through its Python API);
  # the smoke is the imports check alone; meta.mainProgram still names
  # the census spelling for the OS surfaces.
  doInstallCheck = false;

  meta = {
    description = "A dynamic environment to evaluate attacks and defenses for LLM agents (prompt injection benchmark)";
    homepage = "https://github.com/ethz-spylab/agentdojo";
    changelog = "https://github.com/ethz-spylab/agentdojo/commits/${sources.agent-dojo.version}";
    license = lib.licenses.mit;
    mainProgram = "agentdojo";
  };
}
