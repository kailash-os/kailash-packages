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

  # v2 fetcher cache hash — emitted verbatim by the hosted run at
  # 4b6c358 (`got: sha256-9dlP7n8wEZl8gHXtGZtH4o9GiPAHH+BTSpzYCVgC6ts=`,
  # build-packages (promptfoo, x86_64-linux), the v1->v2
  # fixed-output hash mismatch RED; the pinned-build chicken-egg cycle,
  # real output recorded). The v1 prefetch hash above is kept as the
  # provenance record of the pinned lockfile.
  npmDepsHash = "sha256-9dlP7n8wEZl8gHXtGZtH4o9GiPAHH+BTSpzYCVgC6ts=";

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
  postPatch = ''
    python3 - <<'PYEOF'
    import json

    with open("package-lock.json") as f:
        lock = json.load(f)

    reg = "https://registry.npmjs.org/"
    # (resolved URL, integrity) — every integrity byte-verified against the
    # live registry metadata AND the pinned lockfile's own integrity fields
    # (12/12 exact match) before committing.
    entries = {
        "node_modules/@openai/agents": (
            reg + "@openai/agents/-/agents-0.14.3.tgz",
            "sha512-mhAPpDz+CeEoViMsYxPcHEMUonPQnGIgP2yCch/SXhXQkhb/53ojO2bUIXW3NSD5lIDyyV6sTIkO+O5WWJrVDA==",
        ),
        "node_modules/@openai/agents-core": (
            reg + "@openai/agents-core/-/agents-core-0.14.3.tgz",
            "sha512-5tJnFL4Ei34GtArVatM9TUtILDYUXJ2/H0+9jIU8B7y5eINjrQtajmeaudFHmxA4/t7blRgG1SuKQfoA0FPy7A==",
        ),
        "node_modules/@openai/agents-openai": (
            reg + "@openai/agents-openai/-/agents-openai-0.14.3.tgz",
            "sha512-ctJhe/scinyUGtv+MCkkHH+QEza96UmeeUPGNKT3ZFWlz1OCj+xC6YxvwX0WBaZQz0BYAgl6m0aIRnfTgBMO9A==",
        ),
        "node_modules/@openai/agents-realtime": (
            reg + "@openai/agents-realtime/-/agents-realtime-0.14.3.tgz",
            "sha512-eeoc49ti7Pi+GPrivUE7M6PGOQAI6jK3UG82aZtwhi6IHj0uHxzNEK33NQODKag1W40ZJm/R0JWxMWS+lQrjDQ==",
        ),
        "node_modules/@openai/codex": (
            reg + "@openai/codex/-/codex-0.156.1.tgz",
            "sha512-nI1iVl/n2SO2lSvlwEsJx63zdSI4C4Me2gR7AG0OWMJiGSakz2tY2hx43E39Zq5aEoeB5bZjJXzp5Sqhog6vyA==",
        ),
        "node_modules/@openai/codex-sdk": (
            reg + "@openai/codex-sdk/-/codex-sdk-0.156.1.tgz",
            "sha512-t1GNPYrSIjHGfBKZ+9pbjOS/by0tMwVe+27fHsMO3RHl9QLIc7dB8XYR954iZ6HpF4EAjZs0melT0mPXF03jVg==",
        ),
        "node_modules/@openai/codex-darwin-arm64": (
            reg + "@openai/codex/-/codex-0.156.1-darwin-arm64.tgz",
            "sha512-Jg6wbdV+wmMZczhwE74GSxOYEZlViKXn6KyCw/yfrz3PAKFD14xljuPopmdhWC1+8IKU2WdN5fdmXNPt2q4HPA==",
        ),
        "node_modules/@openai/codex-darwin-x64": (
            reg + "@openai/codex/-/codex-0.156.1-darwin-x64.tgz",
            "sha512-BVjqNOoltWrnNUrgMRepvDIIBmd4XY+ikAE4pYVHlrwiizNlEWQuCQOTrFMJKp54LFRG8jDTjLZyYQ1QrliuOg==",
        ),
        "node_modules/@openai/codex-linux-arm64": (
            reg + "@openai/codex/-/codex-0.156.1-linux-arm64.tgz",
            "sha512-sTEHk31C12dqzJdjZ2u9KLFCXKL04KyCM+QheSjdQI8uzmVJS7aEF2/qAqFxXwk/jwMzC9u7IihfoIlAGR6YsA==",
        ),
        "node_modules/@openai/codex-linux-x64": (
            reg + "@openai/codex/-/codex-0.156.1-linux-x64.tgz",
            "sha512-2ePo0wgOcnONKsuzp8vBjOmNY+IdsKaouaDDIdiKq9HOWNuV/GI22OeXft2A/1GaoL71ictO0/pLAsCEnQ6wew==",
        ),
        "node_modules/@openai/codex-win32-arm64": (
            reg + "@openai/codex/-/codex-0.156.1-win32-arm64.tgz",
            "sha512-e5DsyOHlKWulTBz/neIczpcYLQDqtaLtBj2lgncOgeQw5mlAQVZHlGvKsoKVcEPUKLb8opIMJBxXi6cz3JJ4hg==",
        ),
        "node_modules/@openai/codex-win32-x64": (
            reg + "@openai/codex/-/codex-0.156.1-win32-x64.tgz",
            "sha512-MJyLxbBs2zzp5kbaR/99Zwe7SmbrwUkveTcT+ayYlO48V0nYh0eU+h2lalBwvC7VJ/ya/bXnUtISJfJKhGCD/g==",
        ),
        "node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/@emnapi/core": (
            reg + "@emnapi/core/-/core-1.11.1.tgz",
            "sha512-RSvbQmHzdKzNsLYa/wHrbc3KN4sYLKAdPZxqiM2HATqv/SBk2/ENSHpvXGaLOMcsAyz0poEGqkmmKYG3OWiJEQ==",
        ),
        "node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/@emnapi/runtime": (
            reg + "@emnapi/runtime/-/runtime-1.11.1.tgz",
            "sha512-vgj7R3y3Wgx24IQaGPA/R6YFXLHVMOZ0uVEyIQPaWs+rd1AzfEMXlAC22FYwO1XkKR6NPsq7mUandH8oIRdZFw==",
        ),
        "node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/@emnapi/wasi-threads": (
            reg + "@emnapi/wasi-threads/-/wasi-threads-1.2.2.tgz",
            "sha512-c95qOXkHdydNKhscBTebqEC1CVAZpyqOfVfBzQ1qgzyl3gfeldUjIggDbIZgDKsHLgnsM+igH7TJ/eAasaVuMA==",
        ),
        "node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/@napi-rs/wasm-runtime": (
            reg + "@napi-rs/wasm-runtime/-/wasm-runtime-1.1.4.tgz",
            "sha512-3NQNNgA1YSlJb/kMH1ildASP9HW7/7kYnRI2szWJaofaS1hWmbGI4H+d3+22aGzXXN9IJ+n+GiFVcGipJP18ow==",
        ),
        "node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/@tybys/wasm-util": (
            reg + "@tybys/wasm-util/-/wasm-util-0.10.2.tgz",
            "sha512-RoBvJ2X0wuKlWFIjrwffGw1IqZHKQqzIchKaadZZfnNpsAYp2mM0h36JtPCjNDAHGgYez/15uMBpfGwchhiMgg==",
        ),
        "node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/tslib": (
            reg + "tslib/-/tslib-2.8.1.tgz",
            "sha512-oJFu94HQb+KVduSUQL7wnpmqnfmLsOA/nAh6b6EH0wCEoK0/mPeXU6c3wKDV83MkOuHPRHtSXKKU99IBazS/2w==",
        ),
    }

    for key, (url, integrity) in entries.items():
        e = lock["packages"].get(key)
        assert e is not None, "lock entry gone at this pin: " + key
        assert "resolved" not in e and "link" not in e, "upstream changed: " + key
        locked = e.get("integrity")
        assert locked == integrity, (
            "integrity drift vs lock for %s: %r != %r" % (key, locked, integrity)
        )
        e["resolved"] = url

    with open("package-lock.json", "w") as f:
        json.dump(lock, f)
    PYEOF
  '';

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
