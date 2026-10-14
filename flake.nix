{
  description = "kailash-packages — the Kailash tool overlay: bespoke derivations + the tool manifest (independently consumable)";

  nixConfig = {
    extra-substituters = "https://kailash.cachix.org";
    extra-trusted-public-keys = "kailash.cachix.org-1:HnASOtfS7XRjQBrH9umnPljPRjvHeJKDvwZDYXt+sKM=";
  };

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs = inputs@{ self, nixpkgs, flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [ "x86_64-linux" "aarch64-linux" ];
      imports = [ ./flake-parts ];
      perSystem = { pkgs, system, lib ? nixpkgs.lib, ... }: {
        # pkgs/ auto-call via the manifest (KA-02.3): every pkgs/<tool>/
        # dir becomes a package; nixpkgs staples resolve to nixpkgs
        # inside the derivations, bespoke ones to the overlay. The
        # auto-call mirrors the §5.5 `overlays.tools` composition.
        packages = import ./pkgs/auto-call.nix lib pkgs ./pkgs;
        checks = {
          # runs the validator against the flake source tree (src = self) so
          # its relative manifest resolution holds in every context, with
          # pyyaml guaranteed via withPackages — the hosted-runner failure
          # (pyyaml absent, __file__-relative path in a filtered source copy)
          # is the proof the gate needs both. Tools-table half of the gate
          # present since KA-02.2 (entry invariants at KA-05.1); nvfetcher
          # pins + pkgs/ scaffold wired with KA-02.3.
          manifest-wellformed = pkgs.runCommand "manifest-wellformed"
            {
              nativeBuildInputs = [ (pkgs.python3.withPackages (ps: [ ps.pyyaml ])) ];
              src = self;
            } ''
            python3 $src/tests/validate_manifest.py
            touch $out
          '';
          # kailash CLI self-test (KA-14.1): exercises cli/kailash — list
          # against the real manifest (the header-only tools stub prints
          # the category tree rows), info on an absent id exits 1, the
          # --json flag emits valid JSON — with every assertion computed
          # from the parsed manifest DATA (never hardcoded row counts),
          # so the check stays green when the KA-05.x manifest rows land.
          # The checker imports the loader from $src/cli with no PYTHONPATH
          # help: the __file__-relative manifest resolution this lane
          # delivers is proven by construction in the check env.
          kailash-cli-self-test = pkgs.runCommand "kailash-cli-self-test"
            {
              nativeBuildInputs = [ (pkgs.python3.withPackages (ps: [ ps.pyyaml ])) ];
              src = self;
            } ''
            python3 $src/cli/check-kailash-cli.py
            touch $out
          '';
          # Gate leg: wave2-smoke-script (KA-10/11/12 acceptance smokes).
          # The flagship-five acceptance clauses name RECORDED smoke runs
          # (garak --list_probes probe index; pyrit/promptfoo version
          # smokes; ART/counterfit import-checks). tools/wave2-smoke.py is
          # that per-tool smoke; this gate proves its command table — the
          # tool set must equal the packages output THIS flake eval
          # computes (WAVE2_SMOKE_EXPECT_TOOLS from builtins.attrNames of
          # the wave-2 subset), and each tool's smoke command/assertions
          # must match the acceptance shapes. The real smokes run on the
          # build-packages legs (see .github/workflows/build.yml — the
          # per-tool smoke step after the nix build). The ko vm-tests job
          # re-runs the same script per tool in the OS repo's VM once
          # Wave 5's KA-06.3 lands the VM harness (PENDING-VM markers on
          # the lane PR).
          #
          # NOTE on the sandboxed eval: the gate runs with pkgs.nix (the
          # flakes-enabled nix the flake-check runner uses), NOT the
          # barebones nix from nativeBuildInputs whose experimental
          # features were off in the first hosted attempt. --impure allows
          # getFlake on the checkout; the expr is anchored so a missing
          # bespoke derivation fails the gate (tool set != table).
          wave2-smoke-script = pkgs.runCommand "wave2-smoke-script"
            {
              nativeBuildInputs = [ pkgs.nix pkgs.python3 ];
              # the gate's second eval runs INSIDE the sandbox with this
              # derivation's own nix — enable flakes/nix-command for it
              # explicitly (hosted flake-check RED: the barebones nix's
              # experimental features were off)
              env.NIX_CONFIG = ''
                experimental-features = nix-command flakes
                accept-flake-config = true
              '';
              src = self;
            } ''
            export WAVE2_SMOKE_EXPECT_TOOLS="$(
              nix eval --accept-flake-config --raw --impure --expr '
                let f = builtins.getFlake (toString $src); in
                let lib = f.inputs.nixpkgs.lib; in
                with f.packages.x86_64-linux;
                lib.concatStringsSep " " (builtins.sort builtins.lessThan
                  (map (n: (builtins.getAttr n f.packages.x86_64-linux).pname or n)
                    (builtins.filter (n: n == "garak" || n == "pyrit" || n == "promptfoo"
                                        || n == "art" || n == "counterfit")
                      (builtins.attrNames f.packages.x86_64-linux))))'
            )"
            echo "flake-resolved tool set: $WAVE2_SMOKE_EXPECT_TOOLS"
            python3 $src/tools/wave2-smoke.py --dry-run
            touch $out
          '';

          # KA-19.1 exp-wrap generator checks. RED STUB: exp-wrap-generator-self-test
          # asserts the stub generator returns the real garak case (it returns an
          # empty surface — watched RED); exp-wrap-manifest-emit asserts the real
          # manifest's 26-row exp surface is emitted (stub emits none — watched
          # RED). Both go GREEN with the real generator commit.
          exp-wrap-generator-self-test = pkgs.runCommand "exp-wrap-generator-self-test"
            {
              nativeBuildInputs = [ (pkgs.python3.withPackages (ps: [ ps.pyyaml ])) ];
              src = self;
            } ''
            python3 $src/tools/gen-exp-wrap.py --self-test
            touch $out
          '';
          exp-wrap-manifest-emit = pkgs.runCommand "exp-wrap-manifest-emit"
            {
              src = self;
              nativeBuildInputs = [ (pkgs.python3.withPackages (ps: [ ps.pyyaml ])) ];
            } ''
            JSON="$(python3 $src/tools/gen-exp-wrap.py --manifest-file $src/manifest/tools.yaml)"
            COUNT="$(python3 -c 'import json,sys; print(len(json.load(sys.stdin)["exp_ids"]))' <<<"$JSON")"
            echo "exp rows emitted: $COUNT"
            test "$COUNT" -gt 0 || { echo "gen-exp-wrap emitted NO exp rows from the real manifest — the generator is not wired"; exit 1; }
            WRAPN="$(python3 -c 'import json,sys; print(len(json.load(sys.stdin)["wrappers"]))' <<<"$JSON")"
            test "$WRAPN" -eq "$COUNT" || { echo "emitted wrapper count ($WRAPN) != exp_ids count ($COUNT)"; exit 1; }
            touch $out
          '';

          # ---- KA-22 A-3/A-4 packaging gate (kailash-os#22) --------------
          # Two legs over the A-3 (agentic/MCP) + A-4 (supply chain)
          # manifest categories: (1) the row-surface tests (counts,
          # membership, the mcp-inspector-primary-is-o-07 census rule,
          # the 404-upstream rows carrying NO derivation) run as python
          # unittests against the manifest WITH the pkgs/ tree on disk;
          # (2) the flake packages surface must export every bespoke
          # a-03/a-04 derivation the manifest names (pname match on THIS
          # eval). RED stub: at the pre-GREEN commit the six bespoke
          # derivation dirs do not exist — the tests fail (derivation
          # missing on disk) and the surface leg throws; GREEN lands the
          # six dirs and the SAME legs pass through the SAME eval.
          ka22-a3-a4-row-surface = pkgs.runCommand "ka22-a3-a4-row-surface"
            {
              nativeBuildInputs = [ (pkgs.python3.withPackages (ps: [ ps.pyyaml ])) ];
              src = self;
            } ''
            python3 $src/tests/test_ka22_a3_a4_rows.py
            touch $out
          '';
          # The flake packages surface must export every bespoke A-3/A-4
          # derivation the manifest names — proven at EVAL (the pk#51
          # require-in-env shape: throws fail this check BEFORE any build;
          # the builder script is the receipt printer). RED stub: at the
          # pre-GREEN commit the six bespoke derivation dirs do not exist
          # and the exports assert THROWS with its named message; GREEN
          # lands the dirs and the SAME eval passes.
          ka22-a3-a4-packages-surface =
            let
              require = cond: msg: if cond then true else throw msg;
              namesOf = set: name: if set ? "${name}" then (set.${name}.pname or name) else "<absent>";
              pkgsSurface = self.packages.${system};
              a03Exported = [ "mcp-scan" "mcp-guardian" "mcp-remote" "agent-dojo" ];
              a04Exported = [ "guarddog" "picklescan" ];
              # NO-RESURRECTION GUARD (os#210 phantom purge, 2026-10-14): the
              # pre-purge 404-upstream probe rows below were REMOVED from the
              # manifest (registry: kailash-os#210) — the tripwire keeps
              # firing if a derivation ever appears for one of them WITHOUT
              # a verified upstream + a fresh manifest row (the rebuild
              # contract)
              pendRows = [
                "mcp-unsafe-deser-probe" "langchain-vuln-hunter"
                "llm-agent-fuzzer" "mcpoison" "gguf-template-inspector"
                "safetensors-checker" "hf-repo-inspector"
                "namespace-reuse-check" "torch-load-poc"
              ];
              missingA03 = builtins.filter (id: !(pkgsSurface ? "${id}")) a03Exported;
              missingA04 = builtins.filter (id: !(pkgsSurface ? "${id}")) a04Exported;
              leaked = builtins.filter (id: pkgsSurface ? "${id}") pendRows;
              _evalProofs = [
                (require (missingA03 == [ ])
                  "ka22-a3-a4-packages-surface: packages does not export the bespoke A-3 derivations [${builtins.concatStringsSep ", " missingA03}] — the derivation lanes have not landed (KA-22 GREEN)")
                (require (missingA04 == [ ])
                  "ka22-a3-a4-packages-surface: packages does not export the bespoke A-4 derivations [${builtins.concatStringsSep ", " missingA04}] — the derivation lanes have not landed (KA-22 GREEN)")
                (require (leaked == [ ])
                  "ka22-a3-a4-packages-surface: a 404-upstream probe row unexpectedly exports a derivation [${builtins.concatStringsSep ", " leaked}] — the kailash-os#22 404 record must be revisited")
              ];
            in
            pkgs.runCommand "ka22-a3-a4-packages-surface"
              {
                proofs = toString _evalProofs;
              }
              ''
                echo "ka22-a3-a4-packages-surface: ${toString (builtins.length _evalProofs)} eval proofs passed"
                echo "A-3 exports: ${toString (map (n: namesOf pkgsSurface n) a03Exported)}"
                echo "A-4 exports: ${toString (map (n: namesOf pkgsSurface n) a04Exported)}"
                echo "A-3/A-4 derivation-free probe rows (404-upstream record): ${toString pendRows}"
                touch $out
              '';
          # ---- KA-08.4 torch Shape 4 gate (kailash-os#108) ----------------
          # Shape 4 (spec §4.3/D6): NON-GPU pytorch default + an explicit
          # -nvidia variant built only by labelled jobs, never pulled by
          # default. No global cudaSupport flip anywhere (D6) — the
          # variant arg lives inside pkgs/torch-nvidia/default.nix.
          #
          # EVAL-ONLY HARDENED LEG (v2, after the v1 runCommand closure-walk
          # legs stalled hosted flake-check 50+ min on both systems: the
          # env-context walker mounted the torch drv's WHOLE closure graph
          # — 2800+ drvs — for sandbox substitution per leg, on top of a
          # cold-pin nixpkgs eval). The leg is now a trivial runCommand
          # whose env forces an eval-time `builtins.toJSON` of
          # require-style proofs: the assertions fire DURING
          # `nix flake check` EVALUATION (before any build; the builder is
          # a receipt printer that only echoes the proof blob).
          #
          # Proof surfaces are 100% PURE-EVAL-SAFE (probed): torch's own
          # passthru contract (`cudaSupport`, `rocmSupport`,
          # `cudaCapabilities` — nixpkgs exports the cuda-shape since the
          # variant split), drv/outPath distinctness, file presence and
          # packages-surface membership. A derivation-LEVEL drv-text
          # direct-ref scan is NOT expressible here: reading the .drv text
          # is FORBIDDEN in pure eval ("access to absolute path … is
          # forbidden in pure evaluation mode", discovered by running this
          # very leg), and the RED stub's CUDA deps enter TRANSITIVELY via
          # inputDrvs anyway (its 65 direct refs carry 0 cuda names at the
          # pin) — so the non-GPU-default gate rides the passthru
          # contract, which provably separates the shapes:
          #   torchWithCuda (RED stub)  → passthru.cudaSupport = true,
          #                               cudaCapabilities non-empty
          #   cudaSupport=false (GREEN) → passthru.cudaSupport = false,
          #                               cudaCapabilities = [ ] (probed
          #                               on the real pin closures)
          #
          # `.*nvidia` is deliberately NOT a cuda-family token: the
          # cpu-default torch closure's only nvidia-token drv is triton's
          # own upstream 0002-nvidia-driver-short-circuit-before-ldconfig
          # patch (a CPU-build patch shipped by the triton recipe), not a
          # CUDA library.
          #
          # RED stub state (this commit): pkgs/pytorch/default.nix passes
          # through torchWithCuda (passthru.cudaSupport = true) → the
          # non-GPU-default assertion THROWS at eval; pkgs/torch-nvidia is
          # absent → the variant assertions throw. The throws fail flake
          # check at eval, on both systems, in seconds. GREEN swaps the
          # stub body to `torch.override { cudaSupport = false; }` (an
          # explicit cudaSupport=false build that survives a future
          # upstream default flip) and lands pkgs/torch-nvidia.
          #
          # Probe scope: the default-surface proof evals against an
          # allowUnfree-scoped nixpkgs so the CUDA-carrying RED stub
          # evaluates for the scan; GREEN's default (cudaSupport=false)
          # is free-license and needs no scope.
          torch-shape-eval-proofs = pkgs.runCommand "torch-shape-eval-proofs"
            {
              env.PROOFS = builtins.toJSON (let
                torchScope = (import inputs.nixpkgs {
                  inherit system;
                  config.allowUnfree = true;
                }).python3Packages;
                defaultTorch = import (self + "/pkgs/pytorch/default.nix") {
                  inherit lib;
                  python3Packages = torchScope;
                };
                variantFile = self + "/pkgs/torch-nvidia/default.nix";
                variantTorch = if builtins.pathExists variantFile
                  then import variantFile {
                    inherit lib;
                    python3Packages = torchScope;
                  }
                  else null;
                exported = self.packages.${system} ? "pytorch";
              in {
                # the NON-GPU DEFAULT contract (acceptance core): torch's
                # own passthru must say cudaSupport = false — RED stub
                # says true → throw names the offending shape
                torch-cpu-non-GPU-default =
                  if defaultTorch.passthru.cudaSupport == false
                  then true
                  else throw "torch-cpu-shape: FAIL — the default torch carries passthru.cudaSupport = ${lib.boolToString defaultTorch.passthru.cudaSupport}; Shape 4 requires a non-GPU default built with cudaSupport = false (kailash-os#108)";
                torch-cpu-no-rocm =
                  if defaultTorch.passthru.rocmSupport == false
                  then true
                  else throw "torch-cpu-shape: FAIL — the default torch carries passthru.rocmSupport = ${lib.boolToString defaultTorch.passthru.rocmSupport}; the non-GPU default carries no GPU compute backend";
                torch-cpu-cudaCapabilities-empty =
                  if defaultTorch.passthru.cudaCapabilities == [ ]
                  then true
                  else throw "torch-cpu-shape: FAIL — the default torch advertises non-empty passthru.cudaCapabilities (${builtins.toJSON defaultTorch.passthru.cudaCapabilities}); a non-GPU default compiles no GPU kernels";
                # the default must still ship the packages surface
                torch-cpu-packaged =
                  if exported
                  then true
                  else throw "torch-cpu-shape: FAIL — packages.${system}.pytorch is not exported (.nocall still present? the non-GPU default must ship the default packages/matrix surface)";
                torch-cpu-packages-attr = exported;
                # the VARIANT contract: file present, .nocall-excluded
                # from the auto-call surface (never pulled by default),
                # distinct from the default drv, CUDA-flagged by torch's
                # own passthru
                torch-nvidia-variant-present =
                  if variantTorch != null
                  then true
                  else throw "torch-nvidia-shape: FAIL — pkgs/torch-nvidia/default.nix does not exist: the explicit -nvidia variant output is not landed (Shape 4: non-GPU default + explicit variant)";
                torch-nvidia-nocall-excluded =
                  if builtins.pathExists (self + "/pkgs/torch-nvidia/.nocall")
                  then true
                  else throw "torch-nvidia-shape: FAIL — pkgs/torch-nvidia/.nocall is missing: the variant must stay OUT of the auto-call packages/build-matrix default surface (never pulled by default; labelled CI jobs build it explicitly)";
                torch-nvidia-not-in-packages-surface =
                  if !(self.packages.${system} ? "torch-nvidia")
                  then true
                  else throw "torch-nvidia-shape: FAIL — packages.${system}.torch-nvidia exists in the auto-call surface; the variant must never be pulled by default (labelled CI jobs only)";
                torch-nvidia-distinct-from-default =
                  if variantTorch != null && variantTorch.outPath != defaultTorch.outPath
                  then true
                  else throw "torch-nvidia-shape: FAIL — the -nvidia variant outPath equals the default torch outPath; the variant is not a distinct CUDA shape";
                torch-nvidia-cuda-flagged =
                  if variantTorch != null && variantTorch.passthru.cudaSupport == true
                  then true
                  else throw "torch-nvidia-shape: FAIL — the -nvidia variant carries passthru.cudaSupport = ${lib.boolToString (variantTorch.passthru.cudaSupport or false)}; it is not the explicit CUDA variant";
              });
            }
            # The builder is a receipt printer only: every proof above was
            # already asserted at eval (throws fail `nix flake check`
            # before this script ever runs).
            ''
            echo "torch-shape-eval-proofs (KA-08.4, Shape 4):"
            echo "$PROOFS"
            touch $out
          '';

          # ---- KA-25 O-7 gate (kailash-os#25) -----------------------------
          #
          # EVAL-ONLY leg (the KA-08.4 hardened shape — the builder is a
          # receipt printer; every assertion fires during `nix flake
          # check` evaluation, before any build). Proves the O-7 Agent
          # & MCP Operability derivations this lane lands against the
          # manifest rows that route them (the manifest is the single
          # registry):
          #
          #   * every o-07 packaging.status == "bespoke" row has its
          #     packages.<system> export (the auto-call surface mirrors
          #     pkgs/<id>/default.nix) with meta.mainProgram (the OS
          #     gate's mainProgOf convention binds it into the wrapper);
          #   * the exp row count is the manifest's own (7 at the
          #     pre-purge pin; os#210 phantom purge removed 4 of them —
          #     malicious-mcp-poc, insecure-mcp-lab, kailash-container,
          #     headless-agent — so 3 at this pin, gate-checked);
          #   * the grant face (cli/kailash/mcp_server.py) ships the
          #     deny-by-default contract markers (KAILASH_GRANTS /
          #     KAILASH_GRANT_LOG) — the OS-side agent-grants module
          #     mounts the rest (§11.2).
          #
          # The manifest scan is PURE EVAL (the safety-defaults
          # scanToolsYaml technique — row/level line matching, no FOD
          # parse — eval must stay host-agnostic).
          #
          # RED stub state (first commit): the four pkgs/<id>/ dirs do
          # not exist yet → the packages-surface assertions throw at
          # eval, on both systems, in seconds. GREEN: the four
          # derivations land and every assertion passes.
          o-7-deliverables-eval-proofs = pkgs.runCommand "o-7-deliverables-eval-proofs"
            {
              env.PROOFS = builtins.toJSON (let
                # Pure-eval manifest scan (the safety-defaults row-shape
                # contract): `- id: <tool>` rows, `category: <slug>` and
                # `status:`/`level:` lines collected per pending id; a
                # row closes at its NEXT `- id:` (or EOF), so state
                # flushes there. tools.yaml entry blocks are ordered
                # id → … → category → … → packaging(status) → … →
                # safety(level) — the flush-at-next-id walk sees every
                # field before the row closes.
                lines = lib.splitString "\n" (builtins.readFile (self + "/manifest/tools.yaml"));
                step = state: line:
                  let
                    idRow = lib.match " *- id: *([A-Za-z0-9._-]*)" line;
                    catRow = lib.match " *category: *([a-z]-[0-9][0-9]-[a-z-]*)" line;
                    statRow = lib.match " *status: *([a-z]*)" line;
                    lvlRow = lib.match " *level: *([a-z]*)" line;
                    comment = line == "" || lib.match " *#.*" line != null;
                    isO7 = state.pendingCat == "o-07-agent-mcp-operability";
                  in
                    if comment then state
                    else if idRow != null then
                      (if isO7 && state.pendingIsO7row
                       then let closed = [ { id = state.pending; status = state.pendingStatus; level = state.pendingLevel; } ]; in state // { seen = state.seen ++ closed; pending = builtins.head idRow; pendingStatus = ""; pendingLevel = ""; pendingIsO7row = false; }
                       else state // { pending = builtins.head idRow; pendingStatus = ""; pendingLevel = ""; pendingIsO7row = false; })
                    else if catRow != null then
                      state // { pendingCat = builtins.head catRow; pendingIsO7row = builtins.head catRow == "o-07-agent-mcp-operability"; }
                    else if statRow != null then
                      state // { pendingStatus = builtins.head statRow; }
                    else if lvlRow != null then
                      state // { pendingLevel = builtins.head lvlRow; }
                    else state;
                scan = builtins.foldl' step
                  {
                    seen = [ ];
                    pending = "";
                    pendingCat = "";
                    pendingStatus = "";
                    pendingLevel = "";
                    pendingIsO7row = false;
                  }
                  lines;
                # flush the LAST row (no next-id close at EOF)
                lastFlush = if scan.pendingIsO7row && scan.pending != ""
                  then scan.seen ++ [ { id = scan.pending; status = scan.pendingStatus; level = scan.pendingLevel; } ]
                  else scan.seen;
                o7Rows = lastFlush;
                uniqRows = lib.unique o7Rows;
                bespokeIds = map (r: r.id)
                  (builtins.filter (r: r.status == "bespoke") uniqRows);
                expCount = builtins.length
                  (builtins.filter (r: r.level == "exp") uniqRows);
                pkgExported = id: builtins.hasAttr id self.packages.${system};
                pkgMain = id: (self.packages.${system}.${id}.meta.mainProgram
                  or (throw "o-7-gate: packages.${system}.${id} carries no meta.mainProgram — the OS lab gate's mainProgOf convention cannot bind it"));
                # This lane's 4 landed bespoke faces. The os#210 phantom
                # purge (2026-10-14) removed the two first-party
                # DELIVERABLE ids (kailash-container, headless-agent —
                # their claimed upstream repos never existed; registry:
                # kailash-os#210), so the pending named-drop list is
                # empty BY CONSTRUCTION: deliverable rows cannot exist
                # without a verified upstream now (validate_manifest
                # upstream-realism gate, KA-05.1a).
                landedIds = [ "hexstrike-ai" "mcp-kali-server" "kailash-mcp" "mcp-inspector" ];
                pendingIds = [ ];
              in {
                o-7-bespoke-rows-exported = builtins.map (id:
                  if pkgExported id
                  then { inherit id; exported = true; }
                  else throw "o-7-gate: FAIL — manifest row ${id} is packaging.status bespoke but packages.${system}.${id} does not exist (pkgs/${id}/ missing or .nocall)"
                ) landedIds;
                o-7-pending-named-drops-absent = builtins.map (id:
                  if pkgExported id
                  then throw "o-7-gate: FAIL — ${id} resolved on the packages surface, but its derivation lane has NOT landed (the named-drop contract says it resolves null until then — a surprise attr here means something else exported it; audit before trusting the surface)"
                  else { inherit id; pending = true; }
                ) pendingIds;
                o-7-mainProgram-hexstrike = (pkgMain "hexstrike-ai") == "hexstrike-ai";
                o-7-mainProgram-mcpkali = (pkgMain "mcp-kali-server") == "mcp-kali-server";
                o-7-mainProgram-kailashmcp = (pkgMain "kailash-mcp") == "kailash-mcp";
                o-7-mainProgram-inspector = (pkgMain "mcp-inspector") == "mcp-inspector";
                o-7-exp-row-count =
                  if expCount == 3
                  then true
                  else throw "o-7-gate: FAIL — expected 3 exp-class o-07 rows, found ${toString expCount}: the exp routing record drifted (os#210 purge removed 4 exp rows; §11.2 owns this surface)";
                o-7-kailash-mcp-server-module-ships =
                  if builtins.pathExists (self + "/cli/kailash/mcp_server.py")
                  then true
                  else throw "o-7-gate: FAIL — cli/kailash/mcp_server.py missing: kailash-mcp (the manifest-generated MCP face + grant-gated exec surface) is not landed";
                o-7-kailash-mcp-grant-contract =
                  let
                    src = builtins.readFile (self + "/cli/kailash/mcp_server.py");
                    has = builtins.match ".*KAILASH_GRANTS.*" src != null
                      && builtins.match ".*KAILASH_GRANT_LOG.*" src != null
                      && builtins.match ".*deny-by-default.*" src != null;
                  in
                    if has
                    then true
                    else throw "o-7-gate: FAIL — cli/kailash/mcp_server.py lacks the grant contract markers (KAILASH_GRANTS / KAILASH_GRANT_LOG / deny-by-default): the capability-grants v1 face is incomplete";
              });
            }
            # receipt printer — all assertions fired at eval
            ''
            echo "o-7-deliverables-eval-proofs (KA-25, kailash-os#25):"
            echo "$PROOFS"
            touch $out
          '';
        };
      };
      # ---- KA-08.4 (kailash-os#108) — torch Shape-4 variant lines (D6) ---
      #
      # The torch family ships Shape 4: a NON-GPU default plus an explicit
      # -nvidia variant, with NO global cudaSupport flip anywhere (D6).
      #
      #   packages.<system>.pytorch — the non-GPU default (pkgs/pytorch:
      #     torch built with cudaSupport = false explicitly, so the
      #     default stays cuda-free even if an upstream nixpkgs flip ever
      #     changes the plain attr's default). Its closure carries ZERO
      #     cuda-family input derivations — proven per-arch by the
      #     checks.*.torch-cpu-shape leg (drv-closure dep scan).
      #   pkgs/torch-nvidia/default.nix — the explicit CUDA variant
      #     (torch.override { cudaSupport = true; } shape). It carries a
      #     .nocall marker: it is NOT in the auto-call packages surface
      #     and NOT in the default build matrix — it is never pulled by
      #     default. Labelled CI jobs build it explicitly against an
      #     allowUnfree-scoped nixpkgs, e.g.:
      #       nix build --impure --expr 'let fl = builtins.getFlake
      #         (toString ./.); np = fl.inputs.nixpkgs; in
      #         (import (fl.outPath + "/pkgs/torch-nvidia/default.nix")
      #           { lib = np.lib; python3Packages =
      #             (import np { system = "x86_64-linux";
      #                          config.allowUnfree = true; }).python3Packages; })'
      #     (the checks.*.torch-nvidia-shape leg proves the variant
      #     exists, is .nocall-excluded, distinct from the default drv,
      #     and CUDA-carrying — without building it).
      #
      # Documented fallback (spec §4.3): if the nixpkgs variant fights
      # (build breakage, licence churn), the nixvital/ml-pkgs
      # torch-family overlay is the designated fallback source for the
      # variant line — the flake's optional-inputs seam is where it
      # would compose; the default pytorch line stays nixpkgs-native.
      #
      flake.overlays.default =
        let lib = nixpkgs.lib;
        in final: prev:
          import ./pkgs/auto-call.nix lib final ./pkgs;
    };
}
