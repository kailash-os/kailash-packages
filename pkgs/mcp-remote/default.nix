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
  #
  # NOT platform-independent at fetcherVersion 4: the pin's
  # pnpm-lock.yaml carries 20 os/cpu-filtered OPTIONAL snapshots
  # (fsevents os:[darwin]; the esbuild/rollup-family platform
  # optionals) — the fetcher honours the filters, so the store (and
  # its hash) differs per builder OS. Hash-split by libc case with
  # the real per-OS hashes from the hosted CI FOD mismatch receipts
  # (runs 38317207767 + 38324702538): x86_64-linux AND aarch64-linux
  # share ONE hash (TOraN9vd… — the receipts' earlier "per-arch"
  # reading was an artifact of the FIRST run's two different drv
  # revisions evaluating different optional-dep generations; the
  # corrected run proves the split is by LIBC/OS, not by arch:
  # aarch64-linux got TOraN9vd… on the second attempt) and darwin =
  # aamJhNTA… (the original committed hash — validated by the local
  # darwin fetch). A lockfile change re-cycles both arms via the
  # documented RED→hash procedure.
  pnpmDeps = fetchPnpmDeps {
    inherit (finalAttrs) pname version src;
    pnpm = pnpm;
    fetcherVersion = 4;
    hash =
      if stdenv.hostPlatform.isDarwin then "sha256-aamJhNTAzkhZfiaX+W7i9l36MAS0YWexLecU7PFxGb0="
      else "sha256-TOraN9vdVwC7XxzNV7RZt2f5hTKeFexkIZn5EYebSQA=";
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
