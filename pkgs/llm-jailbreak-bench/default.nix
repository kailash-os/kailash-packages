# llm-jailbreak-bench — JailbreakBench as the standardized jailbreak
# robustness DATA pack (manifest id llm-jailbreak-bench, a-02; KA-13.2,
# kailash-os#104).
#
# Data pack: unpackaged passthrough of the PINNED upstream repo (harness
# + metadata at the v1.0.0 tag). Content boundary recorded honestly
# (kailash-os#104 acceptance): the actual behavior corpus rides
# HuggingFace at the harness's runtime (src/jailbreakbench/dataset.py
# loads dedeswim/JBB-Behaviors via HF datasets) — the repo pin carries
# the harness, corpus loaders and repo metadata, NOT a vendored copy of
# the HF corpus. The manifest row's "harness + artifact pack"
# description names exactly this surface.
#
# LICENCE: repo MIT (LICENSE verified at the pin). Content licences of
# downstream corpora the harness consumes are outside this pack.
#
# Pin: tag v1.0.0 → commit rev 518a41a8a3dfdd3aee2a4aeb38f8c162fedb80d7
# (verified via the GitHub API; committer date 2024-06-13T09:00:03Z).
# Fixed-output fetch, sha256 pin — NO auto-update.
{
  lib,
  stdenvNoCC,
  fetchFromGitHub,
}:

stdenvNoCC.mkDerivation {
  pname = "llm-jailbreak-bench";
  version = "1.0.0";

  src = fetchFromGitHub {
    owner = "JailbreakBench";
    repo = "jailbreakbench";
    rev = "518a41a8a3dfdd3aee2a4aeb38f8c162fedb80d7";
    hash = "sha256-mc3D3v/7iMwdD/7sg6JnLDFPHMDM6mZmhqBhR51RuLc=";
  };

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/share/kailash/data/llm-jailbreak-bench"
    cp -a "$src/." "$out/share/kailash/data/llm-jailbreak-bench/"
    runHook postInstall
  '';

  meta = {
    description = "JailbreakBench harness + metadata — the llm-jailbreak-bench DATA pack (a-02; corpus rides HF at runtime)";
    homepage = "https://github.com/JailbreakBench/jailbreakbench";
    license = lib.licenses.mit;
    platforms = lib.platforms.all;
  };
}
