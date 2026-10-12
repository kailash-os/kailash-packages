# mcp-inspector — modelcontextprotocol/inspector, the visual testing tool
# for MCP servers (KA-25, kailash-os#25; plan §3.5 O-7 — the A-3 tool on
# dogfood duty: the CI loop runs the A-3 scanner suite against the
# distro's kailash-mcp).
#
# Node toolchain (the promptfoo recipe lineage, buildNpmPackage):
# pinned to the upstream RELEASE TAG 2.10.1 —
# rev 0d2bc1d91ce177ea8d497ee3efe91bcc59e40a1c (refs/tags/2.10.1; the
# npm dist-tag latest at 2026-10-13 matches 2.10.1). The npm REGISTRY
# tarball carries no lockfile; the git tree does (package-lock.json at
# the tag, the monorepo workspaces lock). Engines node >=22.19 — the
# pin's nodejs is 24.21.0 (probed).
#
# Monorepo posture: the root package is the CLI face (bin.mcp-inspector
# → clients/launcher/build/index.js) with clients/* workspaces (web,
# cli, mcpdo, tui, launcher) + core; the build script chain compiles
# the workspaces into the launcher build the bin points at.
# buildNpmPackage runs npm ci over the committed lockfile; the build
# phase runs the root build script.
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

  # no upstream lifecycle scripts in the sandbox; the build phase runs
  # npm's own build script chain
  npmPackFlags = [ "--ignore-scripts" ];
  makeCacheWritable = true;

  meta = {
    description = "MCP Inspector — visual testing tool for MCP servers (o-07 dogfood duty)";
    homepage = "https://github.com/modelcontextprotocol/inspector";
    license = lib.licenses.asl20;
    mainProgram = "mcp-inspector";
  };
})
