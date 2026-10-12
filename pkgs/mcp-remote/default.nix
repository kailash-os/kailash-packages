# mcp-remote — geelen/mcp-remote, the stdio/HTTP bridge for remote MCP
# transports (KA-22, kailash-os#22; A-3 agentic/MCP tool-use; plan §9
# Phase 5). Shape 2 (node toolchain, §5.3): pnpm toolchain build over
# the committed nvfetcher pin. The manifest row binds this as the
# reachability / MITM-test bridge; safety "requires-target" (a live MCP
# endpoint is the target), which per §11.2 keeps it a package-list
# surface (NOT exp-gated).
#
# Pin: main head 6a06aca546a8fd3b7beb040f39761b364893198d (2026-09-20,
# verified via the GitHub API before committing); package.json version
# 0.1.38 at the pin. MIT.
#
# Toolchain: pnpm (packageManager pnpm@10.11.0; pnpm-lock.yaml committed
# upstream). nixpkgs has NO buildPnpmPackage at this pin — the nodejs /
# pnpmConfigHook shape (fetchPnpmDeps cache + pnpmConfigHook + explicit
# pnpm build/install phases) is the recipe shape nixpkgs' own
# webapp-recipes use at this rev.
{
  lib,
  callPackage,
  stdenv,
  nodejs_22,
  pnpm,
  pnpmConfigHook,
  fetchPnpmDeps,
  writableTmpDirAsHomeHook,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };
in

stdenv.mkDerivation (finalAttrs: {
  pname = "mcp-remote";
  # package.json version at the pin + pin date from _sources.mcp-remote.date
  version = "0.1.38-unstable-2026-09-20";

  src = sources.mcp-remote.src;

  nodejs = nodejs_22;

  # pnpm-deps cache (fixed-output, fetcherVersion 4): the committed
  # pnpm-lock.yaml fetch. Its `pnpm` arg is the SAME pnm the build side
  # runs (pkgs.pnpm) — the pnpm store layout is coupled to the pnpm
  # version (a pnpm-10 fetcher produced a v10-layout store the
  # v10 build-side pnpm could not read → ERR_PNPM_NO_OFFLINE_TARBALL;
  # same-version fetch + install is the shape the nixpkgs recipes use).
  # Hash cycled per the documented RED→hash procedure (FOD content is
  # the pnpm store — platform-independent).
  pnpmDeps = fetchPnpmDeps {
    inherit (finalAttrs) pname version src;
    pnpm = pnpm;
    fetcherVersion = 4;
    hash = "sha256-aamJhNTAzkhZfiaX+W7i9l36MAS0YWexLecU7PFxGb0=";
  };

  nativeBuildInputs = [
    nodejs_22
    pnpm
    pnpmConfigHook
    writableTmpDirAsHomeHook
  ];

  # tsup builds dist/proxy.js + dist/client.js (the two bin entries)
  buildPhase = ''
    runHook preBuild
    pnpm run build
    runHook postBuild
  '';

  doCheck = false;

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/lib/mcp-remote" "$out/bin"
    cp -r . "$out/lib/mcp-remote/"
    rm -rf "$out/lib/mcp-remote/test"
    install -m755 "$out/lib/mcp-remote/dist/proxy.js" "$out/lib/mcp-remote/"
    ln -s "$out/lib/mcp-remote/dist/proxy.js" "$out/bin/mcp-remote"
    ln -s "$out/lib/mcp-remote/dist/client.js" "$out/bin/mcp-remote-client"
    runHook postInstall
  '';

  postInstall = ''
    test -x "$out/bin/mcp-remote" || { echo "mcp-remote: bin/mcp-remote missing"; exit 1; }
  '';

  meta = {
    description = "Remote proxy for Model Context Protocol — connect local-only MCP clients to remote servers over oAuth";
    homepage = "https://github.com/geelen/mcp-remote";
    changelog = "https://github.com/geelen/mcp-remote/commits/${sources.mcp-remote.version}";
    license = lib.licenses.mit;
    mainProgram = "mcp-remote";
  };
})
