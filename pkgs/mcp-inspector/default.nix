# mcp-inspector — modelcontextprotocol/inspector, the visual testing tool
# for MCP servers (KA-25, kailash-os#25; plan §3.5 O-7 — the A-3 tool on
# dogfood duty: the CI loop runs the A-3 scanner suite against the
# distro's kailash-mcp).
#
# Node toolchain (the promptfoo recipe lineage, buildNpmPackage) pinned
# to the upstream RELEASE TAG 2.10.1 — rev 0d2bc1d91ce177ea8d497ee3efe91
# bcc59e40a1c (refs/tags/2.10.1; the npm dist-tag latest at 2026-10-13
# matches 2.10.1). The git tree carries the root package-lock.json (the
# monorepo lock; fetched deps validated green in CI — run 38321435525
# shows the npm-deps FOD + npm ci completing before the failure).
# Engines node >=22.19 — the pin's nodejs is 24.21.0 (probed).
#
# MONOREPO POSTURE (v2 deliberately NOT npm workspaces): each
# clients/* dir keeps its own package.json + node_modules; the root
# postinstall (scripts/install-clients.mjs) cascades per-client npm
# installs that the ROOT lockfile does not cover — ENOTCACHED in the
# offline sandbox (the hosted CI receipts, both systems: run
# 38321435525). The wheel path is NOT available: the 2.10.1 registry
# WHEEL carries NO package-lock.json (the 27-file `files` allowlist —
# no lockfile, and the git-tree dep fetch needs the root lock), so the
# git tree + the script's own official opt-out
# (INSPECTOR_SKIP_CLIENT_INSTALL=1, preConfigure) is the shape. The
# launcher face's runtime deps ride the root lockfile (npm ci's tree,
# fully cached — 359 packages verified in the CI config hook before
# the makeCacheWritable re-run tripped the cascade).
#
# Licence: Apache-2.0 (the repo LICENSE at the tag — the manifest row's
# "MIT→Apache-2.0 transition" note resolves to Apache-2.0 at v2.x).
#
# SAFETY: safety.level "safe" (manifest row) — the ONE non-exp row of
# O-7: resolves into the ordinary package-list surface (no lab gate;
# the dogfood duty runs it against kailash-mcp in CI).
{
  lib,
  fetchFromGitHub,
  buildNpmPackage,
  nodejs,
}:

buildNpmPackage (finalAttrs: {
  pname = "mcp-inspector";
  version = "2.10.1";

  src = fetchFromGitHub {
    owner = "modelcontextprotocol";
    repo = "inspector";
    rev = "0d2bc1d91ce177ea8d497ee3efe91bcc59e40a1c";
    hash = "sha256-dTAD8sBnaAD77fFgrGH/ISRTlXsSur9aLSX+77xouRY=";
  };

  npmDepsHash = "sha256-twig8tHo5mYr4E34HSVkGxg5dEu0/K6RnJ2wlEVzFdU=";

  # The root postinstall cascade must never run in the sandbox.

  # EVERY npm invocation in the sandbox must carry --ignore-scripts:
  # npm ci gets it from the config hook, but npmInstallHook's
  # `npm prune --omit=dev --no-save` does NOT — and npm prune RUNS
  # lifecycle scripts, so the root postinstall cascade
  # (scripts/install-clients.mjs) fired there and ENOTCACHED on
  # clients/web (deps outside the root lockfile — the CI receipts,
  # runs 38321435525 + 38325241587, both systems). npmPruneFlags
  # feeds the prune invocation directly; the
  # INSPECTOR_SKIP_CLIENT_INSTALL=1 env export is belt-and-braces
  # (the script's own official opt-out), set as derivation env so it
  # covers every phase.
  npmPackFlags = [ "--ignore-scripts" ];
  npmPruneFlags = [ "--ignore-scripts" ];
  env = {
    INSPECTOR_SKIP_CLIENT_INSTALL = "1";
  };

  meta = {
    description = "MCP Inspector — visual testing tool for MCP servers (o-07 dogfood duty)";
    homepage = "https://github.com/modelcontextprotocol/inspector";
    license = lib.licenses.asl20;
    mainProgram = "mcp-inspector";
  };
})
