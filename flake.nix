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
        };
      };
      flake.overlays.default =
        let lib = nixpkgs.lib;
        in final: prev:
          import ./pkgs/auto-call.nix lib final ./pkgs;
    };
}
