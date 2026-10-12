# rockyou — the rockyou.txt credential wordlist as a small C-5 DATA pack
# (manifest id pw-packs; KA-29, kailash-os#29).
#
# Data pack NOT a tool: unpackaged byte-identical passthrough of the
# single wordlist artefact. `pw-packs` is the plan §5.3 table's C-5
# data-row id ("C-5 | seclists, pw-packs | data") — this derivation
# carries the small default-ON slice: the classic rockyou breach list,
# the offline-cracking corpus every C-5 flagship (hashcat, john) takes
# as its default dictionary argument.
#
# SIZE vs MEGA: rockyou.txt is 133 MB — this is the small pack
# (`kailash.data.pwPacks`, OS-side default ON per the KA-29 data-pack
# split); the ~1.8 GB full SecLists corpus stays behind the OPT-IN
# kailash-data.wordlists-mega (default OFF; plan §3.2 C-5).
#
# LICENCE: MIT — this is the same 2026.1 SecLists release tag the
# seclists pack pins (rockyou.txt lives in the SecLists tree at
#Passwords/Leaked-Databases/rockyou.txt; nixpkgs' own `rockyou` attr
# extracts it from the identical tarball). Per the manifest row: provenance
# is the NixOS/nixpkgs packaging path (the source of the pin below).
#
# Pin: upstream release TAG 2026.1 → commit rev
# 190c6f7bd58c847ceadfe57d9853592737f059e8 (committer date
# 2026-03-23T05:56:29Z, verified via the GitHub API 2026-10-12); the
# sha256 pin equals the seclists pack's (one tarball, two slices).
# Fixed-output fetch + extraction — NO auto-update (a re-pin is an
# explicit human review).
{
  lib,
  stdenvNoCC,
  fetchFromGitHub,
}:

stdenvNoCC.mkDerivation {
  pname = "rockyou";
  version = "2026.1";

  src = fetchFromGitHub {
    owner = "danielmiessler";
    repo = "SecLists";
    rev = "190c6f7bd58c847ceadfe57d9853592737f059e8";
    hash = "sha256-S1C+/gX3mvCC9OVxzCO6PrzbvxCz5mTWEXrBqzSuKps=";
  };

  # Extract the single wordlist; the corpus rides the seclists pack
  # (this pack's output is the small slice). Upstream ships rockyou
  # tar-gzipped (rockyou.txt.tar.gz, 53 MB compressed → the 133 MB
  # list; nixpkgs' `rockyou` attr untars this exact member).
  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/share/kailash/data/pw-packs"
    tar -xzf "$src/Passwords/Leaked-Databases/rockyou.txt.tar.gz" \
      -C "$out/share/kailash/data/pw-packs"
    test -f "$out/share/kailash/data/pw-packs/rockyou.txt" \
      || { echo "rockyou pack: the tarball member rockyou.txt did not extract at this pin"; exit 1; }
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
