# jailbreak-payloads — the L1B3RT-4S jailbreak corpus as a DATA pack
# (manifest id jailbreak-payloads, a-02; KA-13.2, kailash-os#104; §9
# Phase 4 "payload packs as data derivations").
#
# Data pack NOT a tool: unpackaged, byte-identical corpus passthrough
# (never a buildPythonApplication) — data = packages-repo derivations,
# the OS side composes them (modules/attack/a-02-data-packs.nix, opt-in
# packs.enable, default false).
#
# LICENCE (record-uncertainty rule, kailash-os#104): the repo is
# AGPL-3.0 (LICENSE = GNU AFFERO GENERAL PUBLIC LICENSE v3, verified at
# the pin). The per-vendor prompt FILES (.mkd / .txt .json) are a
# research corpus whose content licences are NOT established per file —
# the manifest row's own description carries the content
# use-restrictions note ("beyond the repo licence"). Therefore:
# opt-in data pack, kept OFF every default profile/ISO (packs.enable
# default false at the OS side) — the derivation ships the corpus
# verbatim and never redistributes it as part of any default surface.
#
# Pin: commit rev 64960b783249d36f76a48a33103cc4b168332b9b (main head,
# committer date 2026-02-17T15:30:36Z, verified via the GitHub API).
# Fixed-output fetch, sha256 pin — NO auto-update (corpora move
# without version discipline; a re-pin is an explicit human review
# with the licence posture re-read). nvfetcher auto-cadence
# deliberately NOT wired (the nvfetcher-cadence activation rule stays
# bespoke-tools-only; a data re-pin is never automated).
{
  lib,
  stdenvNoCC,
  fetchFromGitHub,
}:

stdenvNoCC.mkDerivation {
  pname = "jailbreak-payloads";
  version = "unstable-2026-02-17";

  src = fetchFromGitHub {
    owner = "elder-plinius";
    repo = "L1B3RT4S";
    rev = "64960b783249d36f76a48a33103cc4b168332b9b";
    hash = "sha256-jdHoqR6779kQpO12b01anIPagwm5mXeyiuuDfKwtg+Q=";
  };

  # Corpus passthrough: no build, no patch — the bytes leave the pin
  # untouched (evidence-grade; mutation would break the sha256 pin).
  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/share/kailash/data/jailbreak-payloads"
    cp -a "$src/." "$out/share/kailash/data/jailbreak-payloads/"
    runHook postInstall
  '';

  meta = {
    description = "L1B3RT-4S jailbreak prompt corpus — the jailbreak-payloads DATA pack (a-02)";
    homepage = "https://github.com/elder-plinius/L1B3RT4S";
    license = lib.licenses.agpl3Only;
    platforms = lib.platforms.all;
  };
}
