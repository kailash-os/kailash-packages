# mcp-scan — Invariant's MCP threat scanner (KA-22, kailash-os#22; A-3
# agentic/MCP tool-use; plan §9 Phase 5). Shape 1 (§5.3):
# buildPythonApplication over the committed nvfetcher pin; hatchling
# backend; doCheck = false (the upstream suite needs live-scanner
# fixtures), pythonImportsCheck ["agent_scan"] + an install-time CLI
# smoke as the gate.
#
# CONSOLE-SCRIPT NAME (verified at the pin): upstream's pyproject ships
# the entry point as `snyk-agent-scan` (src/agent_scan, pyproject name
# `snyk-agent-scan` 0.6.8 — Invariant's scanner joined Snyk). The
# manifest row's id/nixos_menu exec is the census spelling mcp-scan; the
# derivation ships upstream's bin name and records the divergence here +
# via meta.mainProgram (the menu generator reads nixos_menu.exec, the
# OS gate reads mainProgram — both surfaces keep the mapping explicit).
#
# Pin: main head 2d3ca361e33452dcfb8e74f7b7db6db0ee08d59e (2026-10-06,
# verified via the GitHub API before committing). Apache-2.0.
#
# Deps (pinned pyproject at the pin, resolved from the locked python
# set): rich, pyjson5, pydantic, lark, psutil, pyyaml, aiohttp,
# rapidfuzz, truststore, regex, detect-secrets all ship in the lock;
# mcp[cli]==1.30.0 — the mcp package's cli extra pulls typer/click;
# nixpkgs' locked mcp carries the cli extra via passthru extras — widen
# the pin (pythonRelaxDeps) rather than hand-adding typer.
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
  pname = "mcp-scan";
  # pyproject version at the pin + pin date from _sources.mcp-scan.date
  version = "0.6.8-unstable-2026-10-06";

  src = sources.mcp-scan.src;
  pyproject = true;

  doCheck = false;

  build-system = with python3.pkgs; [ hatchling ];

  dependencies = with python3.pkgs; [
    aiohttp
    detect-secrets
    lark
    mcp
    psutil
    pydantic
    pyjson5
    pyyaml
    rapidfuzz
    regex
    rich
    truststore
  ];

  # upstream ==-pins (mcp==1.30.0, rich==14.2.0) vs the locked set →
  # widen; the runtime link stays the locked derivation
  pythonRelaxDeps = [
    "mcp"
    "rich"
    "detect-secrets"
  ];

  pythonImportsCheck = [ "agent_scan" ];

  nativeInstallCheckInputs = [ writableTmpDirAsHomeHook ];
  nativeBuildInputs = [ writableTmpDirAsHomeHook ];

  postInstall = ''
    $out/bin/snyk-agent-scan --help
  '';

  meta = {
    description = "Agent supply chain security scanner — tool poisoning, prompt injection and tool-description drift detection for MCP";
    homepage = "https://github.com/invariantlabs-ai/mcp-scan";
    changelog = "https://github.com/invariantlabs-ai/mcp-scan/commits/${sources.mcp-scan.version}";
    license = lib.licenses.asl20;
    mainProgram = "snyk-agent-scan";
  };
}
