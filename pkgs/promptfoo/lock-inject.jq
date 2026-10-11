# Resolved-URL + integrity injection for the 18 lockfile entries the pinned
# promptfoo package-lock.json (upstream main head ce5f743f, 2026-10-10)
# ships WITHOUT `resolved` (newer npm omits the default-registry URL;
# verified by scanning).
#
# Consumed by BOTH derivations via --from-file in postPatch — one
# byte-identical transformation on both sides, so npmConfigHook's
# src-lock vs cache-lock diff passes (hosted RED at 0aa1166: `1c1,44585`)
# and the cache carries canonical URLs + packuments for exactly these
# entries (kills the v2 offline-ETARGET class — hosted REDs at b04d323/
# 4577060). Python-free on purpose: the cache FOD has no python3 (hosted
# REDs at a4b30e7/d367dcb: exit 127); jq rides fetchNpmDeps's forwarded
# nativeBuildInputs instead.
#
# Provenance: every integrity below is byte-verified against the live
# registry metadata AND the pinned lockfile's own integrity fields (12/12
# exact match) before committing; the 6 @tailwindcss/oxide-wasm32-wasi
# sub-deps ship NO integrity field at all in the pin (verified: hosted RED
# at 20d023f) — they get the registry-verified value written. Workspace
# entries (`site`, `src/app`) stay un-resolved — the builder links them.
# Touched keys are asserted unchanged-before-injection so a pin update
# that adds a `resolved` fails the build loudly instead of silently
# diverging (anchored-strip discipline).
#
# Exit semantics: jq -e exits nonzero iff the LAST output is false/null —
# the trailing `true` makes any error() abort the build.

def assert($cond; $msg): if $cond then . else error($msg) end;

def entries:   {
    "node_modules/@openai/agents": {
      "url": "https://registry.npmjs.org/@openai/agents/-/agents-0.14.3.tgz",
      "integrity": "sha512-mhAPpDz+CeEoViMsYxPcHEMUonPQnGIgP2yCch/SXhXQkhb/53ojO2bUIXW3NSD5lIDyyV6sTIkO+O5WWJrVDA=="
    },
    "node_modules/@openai/agents-core": {
      "url": "https://registry.npmjs.org/@openai/agents-core/-/agents-core-0.14.3.tgz",
      "integrity": "sha512-5tJnFL4Ei34GtArVatM9TUtILDYUXJ2/H0+9jIU8B7y5eINjrQtajmeaudFHmxA4/t7blRgG1SuKQfoA0FPy7A=="
    },
    "node_modules/@openai/agents-openai": {
      "url": "https://registry.npmjs.org/@openai/agents-openai/-/agents-openai-0.14.3.tgz",
      "integrity": "sha512-ctJhe/scinyUGtv+MCkkHH+QEza96UmeeUPGNKT3ZFWlz1OCj+xC6YxvwX0WBaZQz0BYAgl6m0aIRnfTgBMO9A=="
    },
    "node_modules/@openai/agents-realtime": {
      "url": "https://registry.npmjs.org/@openai/agents-realtime/-/agents-realtime-0.14.3.tgz",
      "integrity": "sha512-eeoc49ti7Pi+GPrivUE7M6PGOQAI6jK3UG82aZtwhi6IHj0uHxzNEK33NQODKag1W40ZJm/R0JWxMWS+lQrjDQ=="
    },
    "node_modules/@openai/codex": {
      "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.156.1.tgz",
      "integrity": "sha512-nI1iVl/n2SO2lSvlwEsJx63zdSI4C4Me2gR7AG0OWMJiGSakz2tY2hx43E39Zq5aEoeB5bZjJXzp5Sqhog6vyA=="
    },
    "node_modules/@openai/codex-sdk": {
      "url": "https://registry.npmjs.org/@openai/codex-sdk/-/codex-sdk-0.156.1.tgz",
      "integrity": "sha512-t1GNPYrSIjHGfBKZ+9pbjOS/by0tMwVe+27fHsMO3RHl9QLIc7dB8XYR954iZ6HpF4EAjZs0melT0mPXF03jVg=="
    },
    "node_modules/@openai/codex-darwin-arm64": {
      "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.156.1-darwin-arm64.tgz",
      "integrity": "sha512-Jg6wbdV+wmMZczhwE74GSxOYEZlViKXn6KyCw/yfrz3PAKFD14xljuPopmdhWC1+8IKU2WdN5fdmXNPt2q4HPA=="
    },
    "node_modules/@openai/codex-darwin-x64": {
      "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.156.1-darwin-x64.tgz",
      "integrity": "sha512-BVjqNOoltWrnNUrgMRepvDIIBmd4XY+ikAE4pYVHlrwiizNlEWQuCQOTrFMJKp54LFRG8jDTjLZyYQ1QrliuOg=="
    },
    "node_modules/@openai/codex-linux-arm64": {
      "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.156.1-linux-arm64.tgz",
      "integrity": "sha512-sTEHk31C12dqzJdjZ2u9KLFCXKL04KyCM+QheSjdQI8uzmVJS7aEF2/qAqFxXwk/jwMzC9u7IihfoIlAGR6YsA=="
    },
    "node_modules/@openai/codex-linux-x64": {
      "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.156.1-linux-x64.tgz",
      "integrity": "sha512-2ePo0wgOcnONKsuzp8vBjOmNY+IdsKaouaDDIdiKq9HOWNuV/GI22OeXft2A/1GaoL71ictO0/pLAsCEnQ6wew=="
    },
    "node_modules/@openai/codex-win32-arm64": {
      "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.156.1-win32-arm64.tgz",
      "integrity": "sha512-e5DsyOHlKWulTBz/neIczpcYLQDqtaLtBj2lgncOgeQw5mlAQVZHlGvKsoKVcEPUKLb8opIMJBxXi6cz3JJ4hg=="
    },
    "node_modules/@openai/codex-win32-x64": {
      "url": "https://registry.npmjs.org/@openai/codex/-/codex-0.156.1-win32-x64.tgz",
      "integrity": "sha512-MJyLxbBs2zzp5kbaR/99Zwe7SmbrwUkveTcT+ayYlO48V0nYh0eU+h2lalBwvC7VJ/ya/bXnUtISJfJKhGCD/g=="
    },
    "node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/@emnapi/core": {
      "url": "https://registry.npmjs.org/@emnapi/core/-/core-1.11.1.tgz",
      "integrity": "sha512-RSvbQmHzdKzNsLYa/wHrbc3KN4sYLKAdPZxqiM2HATqv/SBk2/ENSHpvXGaLOMcsAyz0poEGqkmmKYG3OWiJEQ=="
    },
    "node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/@emnapi/runtime": {
      "url": "https://registry.npmjs.org/@emnapi/runtime/-/runtime-1.11.1.tgz",
      "integrity": "sha512-vgj7R3y3Wgx24IQaGPA/R6YFXLHVMOZ0uVEyIQPaWs+rd1AzfEMXlAC22FYwO1XkKR6NPsq7mUandH8oIRdZFw=="
    },
    "node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/@emnapi/wasi-threads": {
      "url": "https://registry.npmjs.org/@emnapi/wasi-threads/-/wasi-threads-1.2.2.tgz",
      "integrity": "sha512-c95qOXkHdydNKhscBTebqEC1CVAZpyqOfVfBzQ1qgzyl3gfeldUjIggDbIZgDKsHLgnsM+igH7TJ/eAasaVuMA=="
    },
    "node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/@napi-rs/wasm-runtime": {
      "url": "https://registry.npmjs.org/@napi-rs/wasm-runtime/-/wasm-runtime-1.1.4.tgz",
      "integrity": "sha512-3NQNNgA1YSlJb/kMH1ildASP9HW7/7kYnRI2szWJaofaS1hWmbGI4H+d3+22aGzXXN9IJ+n+GiFVcGipJP18ow=="
    },
    "node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/@tybys/wasm-util": {
      "url": "https://registry.npmjs.org/@tybys/wasm-util/-/wasm-util-0.10.2.tgz",
      "integrity": "sha512-RoBvJ2X0wuKlWFIjrwffGw1IqZHKQqzIchKaadZZfnNpsAYp2mM0h36JtPCjNDAHGgYez/15uMBpfGwchhiMgg=="
    },
    "node_modules/@tailwindcss/oxide-wasm32-wasi/node_modules/tslib": {
      "url": "https://registry.npmjs.org/tslib/-/tslib-2.8.1.tgz",
      "integrity": "sha512-oJFu94HQb+KVduSUQL7wnpmqnfmLsOA/nAh6b6EH0wCEoK0/mPeXU6c3wKDV83MkOuHPRHtSXKKU99IBazS/2w=="
    }
  }
;

. as $root
| $root.packages as $packages
| reduce (entries | to_entries[]) as $e (
    $packages;
    .[$e.key] as $old
    | if $old == null then error("lock entry gone at this pin: " + $e.key) else . end
    | assert($old | has("resolved") | not; "upstream changed (resolved present): " + $e.key)
    | assert($old | has("link") | not; "upstream changed (link present): " + $e.key)
    | if ($old.integrity // null) == null
      then .[$e.key].integrity = $e.value.integrity
      else assert($old.integrity == $e.value.integrity;
                  "integrity drift vs lock for " + $e.key + ": " + $old.integrity + " != " + $e.value.integrity)
      end
    | .[$e.key].resolved = $e.value.url
)
| $root * {packages: .}
