# subfinder — pinned from main (nvfetcher/_sources; KA-02.3 #68).
# Shape 2 (system build — Go, plan §5.3): buildGoModule over the
# committed pin; checkPhase skipped (VM tests cover behaviour), the
# version check is the smoke gate. Recipe lineage: nixpkgs
# pkgs/by-name/su/subfinder, rebuilt against the overlay pin (the
# census marks c-01 nixpkgs-stale — this is the overlay-currency
# path). Pinned rev c97f2580: main @ 2026-10-08 (newer than the
# v2.17.0 tag).
{
  lib,
  callPackage,
  buildGoModule,
  versionCheckHook,
  writableTmpDirAsHomeHook,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };
in
buildGoModule (finalAttrs: {
  pname = "subfinder";
  version = "2.17.0-unstable-2026-10-08";
  __structuredAttrs = true;

  src = sources.subfinder.src;

  # nixpkgs lineage: disable the phone-home update check for
  # deterministic installs (nixpkgs' disable-update-check.patch targets
  # a version-locked context; substituteInPlace is drift-proof)
  postPatch = ''
    substituteInPlace pkg/runner/options.go \
      --replace-fail '"duc", false, "disable automatic subfinder update check"' \
                     '"duc", true, "disable automatic subfinder update check"'
  '';

  # must equal the pinned tree's go.mod; re-verified and updated with
  # every pin update (the update PR carries the build status)
  vendorHash = "sha256-+GBO8ufJp39l7dYl1L1V3g4pFVrDgNNzLBBaFp9C0OU=";

  subPackages = [ "cmd/subfinder/" ];

  ldflags = [ "-s" ];

  nativeInstallCheckInputs = [
    versionCheckHook
    writableTmpDirAsHomeHook
  ];
  versionCheckKeepEnvironment = [ "HOME" ];
  doInstallCheck = true;

  meta = {
    description = "Subdomain discovery tool (passive framework for bug bounties)";
    homepage = "https://github.com/projectdiscovery/subfinder";
    changelog = "https://github.com/projectdiscovery/subfinder/commits/${sources.subfinder.version}";
    license = lib.licenses.mit;
    mainProgram = "subfinder";
  };
})
