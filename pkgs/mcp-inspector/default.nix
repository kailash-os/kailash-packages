# mcp-inspector — modelcontextprotocol/inspector, the visual testing tool
# for MCP servers (KA-25, kailash-os#25; spec §2.5 O-7 — the A-3 tool on
# dogfood duty: the CI loop runs the A-3 scanner suite against the
# distro's kailash-mcp).
#
# SHAPE (settled by the hosted CI receipts, in order):
#
#   1. git-tree + buildNpmPackage (535afef): the npm-deps FOD + npm ci
#      --ignore-scripts were GREEN (359 packages, fully cached), but the
#      build chain broke: `npm run build` → build:web →
#      `cd clients/web && npm run build` (tsc -b + vite build) needs
#      clients/web/node_modules — the web client's OWN deps (41, its own
#      package-lock; @testing-library/jest-dom, express types, …) which
#      the ROOT lockfile does not carry (v2 deliberately dropped npm
#      workspaces). The only official installer of per-client deps is
#      the root postinstall cascade (scripts/install-clients.mjs) — it
#      needs network (ENOTCACHED offline; receipts 38321435525). With
#      the cascade skipped, tsc found NO types → 2033 errors
#      (receipt 38325241587). THE GIT-TREE BUILD IS NETWORK-GATED BY
#      DESIGN — impossible offline for ALL FIVE clients, not just web.
#
#   2. THE WHEEL IS THE ANSWER, and it needs NO build: the npm
#      REGISTRY WHEEL @modelcontextprotocol/inspector 2.10.1 ships the
#      PREBUILT client surfaces (clients/web/dist + clients/*/build —
#      the `files` allowlist) and its bin entries point at them. The
#      earlier wheel attempt was rejected for a lockfile-gap; settled
#      here: the wheel's 22 runtime deps synthesize a deterministic
#      package-lock (npm install --package-lock-only over the wheel's
#      package.json — 396-package tree, committed IN-REPO beside this
#      derivation at pkgs/mcp-inspector/package-lock.json), fetchNpmDeps
#      fetches THAT lock, npm ci --ignore-scripts installs the runtime
#      tree, npmInstallHook installs the wheel's allowlisted files +
#      pruned node_modules. dontNpmBuild: nothing compiles — the
#      wheel's dist IS the build output (the same artefact the registry
#      serves its users).
#
# Engines node >=22.19 — the pin's nodejs is 24.21.0 (probed).
# Licence: Apache-2.0 (the repo LICENSE / wheel package.json license
# field at 2.10.1). SAFETY: "safe" row — the ONE non-exp O-7 row (the
# dogfood duty runs it against kailash-mcp in CI).
#
# Receipts (the watched-RED trail for this shape): 38321435525 and
# 38325241587 — ENOTCACHED (the cascade) then 2033 tsc errors (the
# cascade skipped but the per-client deps missing); the wheel +
# synthesized lock is the flip.
{
  lib,
  buildNpmPackage,
  fetchurl,
  runCommand,
  nodejs,
}:

let
  wheel = fetchurl {
    url = "https://registry.npmjs.org/@modelcontextprotocol/inspector/-/inspector-2.10.1.tgz";
    hash = "sha256-F4aAOq8FhEWq9keXPoSPelwXORuZvW4X3bAbY9SufJY=";
  };
  # The wheel unpacks to `package/` — re-root it to a source WITH the
  # committed synthesized lockfile (the registry wheel ships none; the
  # 396-package lock pins exactly the wheel's declared runtime deps).
  srcWithLock = runCommand "mcp-inspector-2.10.1-source" { } ''
    mkdir -p "$out"
    tar -xzf ${wheel} -C "$out" --strip-components=1
    cp ${./package-lock.json} "$out/package-lock.json"
  '';
in

buildNpmPackage (finalAttrs: {
  pname = "mcp-inspector";
  version = "2.10.1";

  src = srcWithLock;

  # cycled placeholder — set from the FOD got: receipt on first build
  npmDepsHash = "sha256-dLUI9CqY/3PXKHvxUE+kG5Lu+k4fmRf8qfMMwUds+CQ=";

  # The published wheel ships PREBUILT clients — nothing compiles.
  # The wheel's postinstall (install-clients.mjs) is a verified no-op
  # on the wheel source (its per-client guard finds no package.json
  # under clients/*; tested standalone, exit 0) AND scripts stay
  # ignored at both npm ci (config hook) and npm prune (the install
  # hook) — the env belt-and-braces is the script's own official
  # opt-out.
  npmPackFlags = [ "--ignore-scripts" ];
  npmPruneFlags = [ "--ignore-scripts" ];
  dontNpmBuild = true;
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
