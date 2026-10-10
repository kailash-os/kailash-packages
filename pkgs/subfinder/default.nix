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
  writableTmpDirAsHomeHook,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };

  # Upstream's build-time version constant (`const version` in
  # pkg/runner/banners.go at the pinned rev c97f2580). Re-verified at
  # every pin update — a pin drift changes the constant and the smoke
  # gate below fails the build (KA-05's manifest carries the declared
  # version for consumers; the packages-repo bug issue has the
  # hosted-build evidence).
  upstreamVersion = "v2.17.0";
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
  # every pin update (the update PR carries the build status). The first
  # hosted build (KA-15.1 build.yml) caught the recorded value stale —
  # the FOD hash below is the hosted-build `got:` value.
  vendorHash = "sha256-0aHBXN/Yd8hiZcowUUQy65vZI2rvLCHCk+QihjjtZrw=";

  subPackages = [ "cmd/subfinder/" ];

  ldflags = [ "-s" ];

  nativeInstallCheckInputs = [
    writableTmpDirAsHomeHook
  ];
  doInstallCheck = true;

  # Smoke gate. nixpkgs' versionCheckHook greps the derivation's
  # version string and is unusable on a rev pin: the nvfetcher version
  # (2.17.0-unstable-2026-10-08) carries the `-unstable-<date>` suffix
  # the binary can never report — nixpkgs' own recipe passes only
  # because it builds a tag whose version string matches upstream's
  # source constant. The honest pin check asserts the constant the
  # pinned tree actually declares (upstreamVersion above).
  installCheckPhase = ''
    runHook preInstallCheck
    output="$("$out/bin/subfinder" --version 2>&1)" || true
    echo "$output"
    echo "$output" | grep -q "Current Version: ${upstreamVersion}" || {
      echo "subfinder version smoke gate: the pinned tree's version constant drifted from the recorded pin (wanted ${upstreamVersion}) — re-verify banners.go at the new pin and update upstreamVersion"
      exit 1
    }
    runHook postInstallCheck
  '';

  meta = {
    description = "Subdomain discovery tool (passive framework for bug bounties)";
    homepage = "https://github.com/projectdiscovery/subfinder";
    changelog = "https://github.com/projectdiscovery/subfinder/commits/${sources.subfinder.version}";
    license = lib.licenses.mit;
    mainProgram = "subfinder";
  };
})
