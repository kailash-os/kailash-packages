# seclists — the SecLists corpus as the kailash-data.wordlists-mega DATA
# pack (manifest id seclists, c-05; KA-29, kailash-os#29); plan §3.2 C-5
# "seclists ~100 MB behind `kailash-data.wordlists-mega`".
#
# Data pack NOT a tool:unpackaged, byte-identical corpus passthrough
# (never a buildPythonApplication) — data = packages-repo derivations,
# the OS side composes them (modules/base/kailash-data.nix on the OS
# side; the OS-side `kailash.data.wordlistsMega` toggle is OPT-IN and
# default-OFF by construction).
#
# SIZE (the reason this is a data pack, never a category-module row):
# the pinned tarball unpacks to ~1.8 GB across 9 top-level classes — it
# rides NO default profile/ISO (plan §8.1: "the wordlist packs are
# excluded from every default ISO by construction").
#
# LICENCE: the repo is MIT (LICENSE verified upstream at the pin; the
# SecLists README states the repository MIT). Per-file corpus content
# from third-party breaches/compilations is NOT relicensed by the repo
# licence — the manifest row's description carries the record; opt-in
# keeps that posture honest (an operator pulling this pack reads the
# corpus's own provenance notes).
#
# Pin: upstream release TAG 2026.1 → commit rev
# 190c6f7bd58c847ceadfe57d9853592737f059e8 (committer date
# 2026-03-23T05:56:29Z, verified via the GitHub API 2026-10-12; the tag
# is the nixpkgs pin too — nixpkgs' own seclists/rockyou fetch
# this exact tarball). Fixed-output fetch, sha256 pin — NO auto-update
# (corpora move without version discipline; a re-pin is an explicit
# human review with the licence posture re-read; nvfetcher cadence
# deliberately NOT wired — the nvfetcher-cadence activation rule stays
# bespoke-tools-only).
{
  lib,
  stdenvNoCC,
  fetchFromGitHub,
}:

stdenvNoCC.mkDerivation {
  pname = "seclists";
  version = "2026.1";

  src = fetchFromGitHub {
    owner = "danielmiessler";
    repo = "SecLists";
    rev = "190c6f7bd58c847ceadfe57d9853592737f059e8";
    hash = "sha256-S1C+/gX3mvCC9OVxzCO6PrzbvxCz5mTWEXrBqzSuKps=";
  };

  # Corpus passthrough: no build, no patch — the bytes leave the pin
  # untouched (evidence-grade; mutation would break the sha256 pin).
  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/share/kailash/data/seclists"
    cp -a "$src/." "$out/share/kailash/data/seclists/"
    runHook postInstall
  '';

  meta = {
    description = "SecLists security wordlist corpus — the kailash-data.wordlists-mega DATA pack (c-05)";
    homepage = "https://github.com/danielmiessler/SecLists";
    license = lib.licenses.mit;
    platforms = lib.platforms.all;
  };
}
