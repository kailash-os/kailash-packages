# promptfoo — promptfoo/promptfoo, the LLM eval/red-team CLI (KA-11.2 #83).
# Node toolchain (Shape 2-adjacent: buildNpmPackage, spec §4.1 population
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
  fetchNpmDeps,
  jq,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };
in

buildNpmPackage (finalAttrs: {
  pname = "promptfoo";
  # package.json version at the pin + pin date from _sources.promptfoo.date
  version = "0.124.1-unstable-2026-10-10";

  src = sources.promptfoo.src;

  # npm-deps cache hash — the v2 prefetch hash of the INJECTED cache
  # (the lock-inject program bakes the 18 resolved URLs + the oxide
  # sub-deps' integrity + their packuments into the cache, which is the
  # fix itself). Provenance: real FOD build on the authoring host
  # (aarch64-darwin) against the flake's own nixpkgs input with the
  # shared program wired verbatim — the documented RED→hash cycle ran
  # locally end-to-end, `got:
  # sha256-sJCHf1tMMuUYSJx+LR5q0w1vI2vjTLQCDaCgehHuWCs=` from the
  # hash-mismatch RED (the cache content is the npm cacache store —
  # content-addressed, platform-independent). Precedent for the
  # procedure: the pre-injection cache hash at 4b6c358
  # (sha256-9dlP7n8wEZl8gHXtGZtH4o9GiPAHH+BTSpzYCVgC6ts=, hosted
  # v1→v2 RED, kept in the trail for provenance — the pre-injection
  # cache cannot satisfy the post-injection src lockfile).
  npmDepsHash = "sha256-sJCHf1tMMuUYSJx+LR5q0w1vI2vjTLQCDaCgehHuWCs=";

  # node >= 22's npm requires the v2 registry cache fetcher (npm config
  # fetcher) — hosted CI RED at 4577060: `npm error code ENOTCACHED /
  # cache mode is 'only-if-cached' but no cached response is available`
  # on @openai/codex-sdk under the v1 fetcher; the builder's remedy #1
  # is this switch.
  npmDepsFetcherVersion = 2;

  # The pinned lockfile omits `resolved` for 18 registry entries (newer
  # npm omits the default-registry URL; verified by scanning — @openai/
  # codex{,-sdk,-darwin-arm64,…} plus six @tailwindcss/oxide-wasm32-wasi
  # sub-deps). The v2 fetcher's cache carries only locked tarballs, so
  # npm's in-sandbox packument re-resolution of those ranges fails
  # (hosted CI RED at b04d323: `npm error code ETARGET — No matching
  # version found for @openai/codex-sdk@0.156.1`; 0.156.1 IS on the
  # registry — probed). postPatch injects the canonical resolved URL +
  # integrity for exactly those 18 entries; every integrity below is
  # byte-verified against BOTH the pinned lockfile entries and the
  # live registry metadata before committing (12/12 match — no
  # invented data; the workspace entries `site`/`src/app` stay
  # un-resolved, the builder links them).
  #
  # The injection is ONE shared jq program (./lock-inject.jq) applied to
  # BOTH derivations, so the two package-lock.json variants stay
  # byte-identical by construction:
  #   - the npm-deps cache FOD (the lock baked INTO its artifact is what
  #     npmConfigHook's postPatch validation diffs the src lockfile
  #     against, hosted RED at 0aa1166 `1c1,44585`; python-free per the
  #     exit-127 lesson at a4b30e7/d367dcb, jq rides fetchNpmDeps's
  #     forwarded nativeBuildInputs),
  #   - the main build (where npm ci runs against the cache — the hook
  #     runs npm ci itself inside postPatchHooks, so the injected lock
  #     must exist BEFORE the hook executes).
  # With both locks carrying the canonical resolved URLs + integrity,
  # prefetch-npm-deps (v2) bakes the packuments into the cache and the
  # offline npm ci finds every entry. npmDepsHash is the v2 prefetch
  # hash of the INJECTED-lock cache — cycled per the documented RED→hash
  # procedure when the program or pin changes.
  postPatch = ''
    # Shared injection program (byte-identical on both sides — see the
    # comment above): deterministic, python-free, anchored asserts fail
    # the build loudly if the lock's shape moves at a new pin.
    jq -e -c --from-file ${./lock-inject.jq} package-lock.json > .package-lock.json.tmp
    mv .package-lock.json.tmp package-lock.json
  '';

  # The npm-deps fixed-output derivation does NOT inherit the top-level
  # nativeBuildInputs (fetchNpmDeps composes its own stdenvNoCC drv —
  # hosted CI REDs at a4b30e7/d367dcb: `python3: command not found` in
  # its patchPhase, exit 127). The cache gets the SAME jq injection as
  # the main build via fetchNpmDeps's forwarded postPatch +
  # nativeBuildInputs (verified at the flake's nixpkgs rev): the lock
  # baked into the cache artifact then matches the src lockfile
  # byte-for-byte for npmConfigHook's validation, and prefetch-npm-deps
  # (v2) bakes the packuments for the injected resolved URLs into the
  # cache — what npm ci's offline mode needs for exactly those entries.
  # The recorded npmDepsHash is the v2 prefetch hash of this injected
  # cache; the change from the pre-injection cache is LEGITIMATE (that
  # is the fix) and its hash is cycled per the documented RED→hash
  # procedure on the next hosted run.
  npmDeps = fetchNpmDeps {
    inherit (finalAttrs) src;
    name = "${finalAttrs.pname}-${finalAttrs.version}-npm-deps";
    hash = finalAttrs.npmDepsHash;
    fetcherVersion = 2;
    nativeBuildInputs = [ jq ];
    postPatch = ''
      jq -e -c --from-file ${./lock-inject.jq} package-lock.json > .package-lock.json.tmp
      mv .package-lock.json.tmp package-lock.json
    '';
  };

  # jq for the postPatch lockfile injection in THIS derivation too (same
  # shared program — the main build's npm ci needs the resolved URLs).
  nativeBuildInputs = [ jq ];

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
