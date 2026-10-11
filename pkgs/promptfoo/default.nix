# promptfoo — promptfoo/promptfoo, the LLM eval/red-team CLI (KA-11.2 #83).
# Node toolchain (Shape 2-adjacent: buildNpmPackage, plan §5.1 population
# 2 stale-native override decision → bespoke per the freshness verdict
# below), pinned via nvfetcher.
#
# FRESHNESS DECISION (recorded per §5.4 population 2): nixpkgs' promptfoo
# at the lock is 0.118.14 (pkgs/by-name/pr/promptfoo/package.nix, npm
# publish 2025-10-09) vs upstream latest 0.124.1 (npm publish 2026-10-08,
# ~30 patch releases in the window) — promptfoo is §8.5 fast-moving
# (weekly churn), so a stale-override wrapping would chase nixpkgs'
# year-old recipe surface (tag fetch + lockfile hash + workspace preFixup
# all re-derived under the override anyway). Verdict: BESPOKE
# buildNpmPackage pin at the upstream main head (ce5f743f, 2026-10-10;
# package.json version 0.124.1 at the pin — a few commits past the
# 0.124.1 tag, the house git-source pattern), re-evaluated at each
# release per §8.5's stale-native row.
#
# Recipe lineage: nixpkgs' own recipe (mined per house discipline) —
# shape kept: buildNpmPackage + finalAttrs, PLAYWRIGHT_SKIP_BROWSER_
# DOWNLOAD (no browser binary in the sandbox), preFixup cleanup of the
# dangling workspace symlinks (src/app + site workspaces are repo-dev
# surfaces, not runtime). npmDepsHash = prefetch-npm-deps over the
# PINNED package-lock.json (real hash, obtained from the pinned tree).
#
# Licence: MIT (upstream repo/package.json, verified at the pin).
# Update cadence: §8.5 fast-moving — weekly nvfetcher dry-run class.
{
  lib,
  callPackage,
  buildNpmPackage,
  nodejs,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };
in

buildNpmPackage (finalAttrs: {
  pname = "promptfoo";
  # package.json version at the pin + pin date from _sources.promptfoo.date
  version = "0.124.1-unstable-2026-10-10";

  src = sources.promptfoo.src;

  npmDepsHash = "sha256-C0fX8U89emmsTiZDO7u+/hDYCQxSKLXcFar/2tqly08=";

  # don't fetch the playwright browser binary in the build sandbox
  env.PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = "1";

  # cleanup dangling symlinks for the app/site workspaces (nixpkgs
  # recipe pattern — those workspaces are the repo's dev surfaces)
  preFixup = ''
    rm -rf $out/lib/node_modules/promptfoo/node_modules/app $out/lib/node_modules/promptfoo/node_modules/promptfoo-docs
  '';

  doCheck = false;

  # `promptfoo --version` is the smoke gate; the build sandbox has no
  # interactive target, and node modules resolve at require time —
  # the hosted build leg proves the build; the version smoke is
  # recorded PENDING with the exact command in the PR (no fabricated
  # transcripts).
  postInstall = ''
    $out/bin/promptfoo --version
  '';

  meta = {
    description = "Test your prompts, models, RAGs — evaluate and compare LLM outputs, catch regressions, run red-team probes";
    homepage = "https://github.com/promptfoo/promptfoo";
    changelog = "https://github.com/promptfoo/promptfoo/commits/${sources.promptfoo.version}";
    license = lib.licenses.mit;
    mainProgram = "promptfoo";
  };
})
