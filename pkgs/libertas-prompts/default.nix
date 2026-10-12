# libertas-prompts — the L1B3RT-4S corpus as the vendor-organized
# prompt data pack (manifest id libertas-prompts, a-02; KA-13.2,
# kailash-os#104). Twin of the jailbreak-payloads pack over the SAME
# upstream (the manifest rows are the plan's L1B3RT-4S twins: the
# jailbreak-payloads row packages the corpus, the libertas-prompts row
# keys the vendor-organized views) — one upstream pin, two manifest
# rows, exactly like the §5.2 one-derivation-many-tags posture.
#
# Data pack: unpackaged byte-identical passthrough (see the sibling
# jailbreak-payloads derivation for the full licence-position comment:
# repo AGPL-3.0, per-file content licences NOT established per file —
# opt-in data pack, never on default profiles/ISOs; packs.enable
# default false at the OS side).
#
# Pin: commit rev 64960b783249d36f76a48a33103cc4b168332b9b (main head,
# committer date 2026-02-17T15:30:36Z, verified via the GitHub API).
# Fixed-output fetch, sha256 pin — NO auto-update.
{
  lib,
  stdenvNoCC,
  fetchFromGitHub,
}:

stdenvNoCC.mkDerivation {
  pname = "libertas-prompts";
  version = "unstable-2026-02-17";

  src = fetchFromGitHub {
    owner = "elder-plinius";
    repo = "L1B3RT4S";
    rev = "64960b783249d36f76a48a33103cc4b168332b9b";
    hash = "sha256-jdHoqR6779kQpO12b01anIPagwm5mXeyiuuDfKwtg+Q=";
  };

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/share/kailash/data/libertas-prompts"
    cp -a "$src/." "$out/share/kailash/data/libertas-prompts/"
    runHook postInstall
  '';

  meta = {
    description = "L1B3RT-4S vendor-organized jailbreak prompt corpus — the libertas-prompts DATA pack (a-02)";
    homepage = "https://github.com/elder-plinius/L1B3RT4S";
    license = lib.licenses.agpl3Only;
    platforms = lib.platforms.all;
  };
}
