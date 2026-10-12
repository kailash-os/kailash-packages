# pw-packs — the small C-5 credential-wordlist DATA pack (manifest id
# pw-packs; KA-29, kailash-os#29): rockyou.txt, the classic breach
# corpus every C-5 flagship (hashcat, john) takes as its default
# dictionary argument.
#
# Data pack NOT a tool: unpackaged byte-identical passthrough of the
# single wordlist artefact — data = packages-repo derivations, the OS
# side composes them (modules/base/kailash-data.nix;
# kailash.data.pwPacks is OPT-IN and default-OFF; the OS check legs
# assert the defaults-false posture BOTH directions). §5.3 emit table:
# "C-5 | seclists, pw-packs | data" — two rows, one upstream (the
# 2026.1 SecLists release; dir name == manifest id per the
# emit-matrix bijection).
#
# LICENCE: the repo is MIT (LICENSE verified at the pin via the GitHub
# API 2026-10-13). The rockyou.txt breach list itself is a third-party
# compilation NOT relicensed by the repo licence — the manifest row's
# description carries the record; opt-in only keeps that posture
# honest. Packaging provenance note: nixpkgs' own `rockyou` attr
# extracts the same member from the same tarball (the shape the
# derivation mirrors).
#
# Pin: upstream release TAG 2026.1 → commit rev
# 190c6f7bd58c847ceadfe57d9853592737f059e8 (committer date
# 2026-03-23T05:56:29Z, verified via the GitHub API 2026-10-13); the
# sha256 pin equals the seclists pack's fetch (one tarball, two
# slices). Fixed-output fetch + extraction — NO auto-update (a re-pin
# is an explicit human review with the licence posture re-read;
# nvfetcher cadence deliberately NOT wired).
{ lib, stdenvNoCC, fetchFromGitHub }:

stdenvNoCC.mkDerivation {
  pname = "rockyou";
  version = "2026.1";

  src = fetchFromGitHub {
    owner = "danielmiessler";
    repo = "SecLists";
    rev = "190c6f7bd58c847ceadfe57d9853592737f059e8";
    hash = "sha256-S1C+/gX3mvCC9OVxzCO6PrzbvxCz5mTWEXrBqzSuKps=";
  };

  # Extract the single wordlist; the full corpus rides the seclists
  # pack (this pack's output is the small slice). Upstream ships
  # rockyou tar-gzipped at Passwords/Leaked-Databases/rockyou.txt.tar.gz
  # (53 MB compressed → the ~133 MB list; nixpkgs' `rockyou` attr
  # untars the same member from the same 2026.1 tarball).
  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/share/kailash/data/pw-packs"
    tar -xzf "$src/Passwords/Leaked-Databases/rockyou.txt.tar.gz" \
      -C "$out/share/kailash/data/pw-packs"
    test -f "$out/share/kailash/data/pw-packs/rockyou.txt" \
      || { echo "pw-packs: the tarball member rockyou.txt did not extract at this pin"; exit 1; }
    chmod 644 "$out/share/kailash/data/pw-packs/rockyou.txt"
    runHook postInstall
  '';

  meta = {
    description = "rockyou.txt credential wordlist — the pw-packs small DATA pack (c-05)";
    homepage = "https://github.com/danielmiessler/SecLists";
    license = lib.licenses.mit;
    platforms = lib.platforms.all;
  };
}
