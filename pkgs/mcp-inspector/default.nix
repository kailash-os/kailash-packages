# mcp-inspector — modelcontextprotocol/inspector, the visual testing tool
# for MCP servers (KA-25, kailash-os#25; plan §3.5 O-7 — the A-3 tool on
# dogfood duty: the CI loop runs the A-3 scanner suite against the
# distro's kailash-mcp).
#
# Node toolchain (the promptfoo recipe lineage, buildNpmPackage) over the
# npm REGISTRY TARBALL @modelcontextprotocol/inspector 2.10.1 (dist-tag
# latest at 2026-10-13; hash probed). The tarball ships the PREBUILT
# client surfaces (clients/*/{build,dist}) — `files` allows only the
# build outputs + the install script, no per-client package.json — so
# the root postinstall cascade (scripts/install-clients.mjs) is a
# verified NO-OP on this source: its per-client guard finds no
# package.json to drive (the git-tree build path is what needs the
# cascade; the published wheel does not). The v2 package deliberately
# does NOT use npm workspaces — each clients/* dir keeps its own deps
# at RUNTIME in the sandbox of the CLIENT surface, not the CLI face;
# the cli bin resolves its runtime deps through the single root
# package.json (the launcher's node_modules), all covered by
# fetch-npm-deps over the tarball's committed package-lock.
#
# The GIT TREE (the earlier attempt) is the WRONG source for this shape:
# its postinstall cascade runs per-client npm installs that the root
# lockfile does not cover (ENOTCACHED in the sandbox — the hosted CI
# receipts). Registry tarball + buildNpmPackage = the correct Shape 4
# (the published-wheel recipe lineage: npm ci over the tarball lock,
# NO build phase — dist/ ships prebuilt).
#
# Engines node >=22.19 — the pin's nodejs is 24.21.0 (probed).
#
# Licence: Apache-2.0 (the package.json license field at 2.10.1 — the
# manifest row's "MIT→Apache-2.0 transition" note resolves to
# Apache-2.0 at v2.x).
#
# SAFETY: safety.level "safe" (manifest row) — the ONE non-exp row of
# O-7: resolves into the ordinary package-list surface (no lab gate;
# the dogfood duty runs it against kailash-mcp in CI).
{
  lib,
  buildNpmPackage,
  fetchurl,
  nodejs,
}:

buildNpmPackage (finalAttrs: {
  pname = "mcp-inspector";
  version = "2.10.1";

  src = fetchurl {
    url = "https://registry.npmjs.org/@modelcontextprotocol/inspector/-/inspector-2.10.1.tgz";
    hash = "sha256-F4aAOq8FhEWq9keXPoSPelwXORuZvW4X3bAbY9SufJY=";
  };

  npmDepsHash = "sha256-dLUI9CqY/3PXKHvxUE+kG5Lu+k4fmRf8qfMMwUds+CQ=";

  # The published wheel ships PREBUILT clients — no compile step; the
  # postinstall cascade is already a verified no-op on this source
  # (its per-client guard finds no package.json under clients/*) but
  # belt-and-braces the official skip keeps the sandbox offline.
  npmInstallFlags = [ "--foreground-scripts=false" ];
  makeCacheWritable = false;
  preConfigure = ''
    export INSPECTOR_SKIP_CLIENT_INSTALL=1
  '';

  # nothing to build: dist/ + clients/*/build + clients/*/dist are
  # committed in the wheel
  dontNpmBuild = true;

  meta = {
    description = "MCP Inspector — visual testing tool for MCP servers (o-07 dogfood duty)";
    homepage = "https://github.com/modelcontextprotocol/inspector";
    license = lib.licenses.asl20;
    mainProgram = "mcp-inspector";
  };
})
