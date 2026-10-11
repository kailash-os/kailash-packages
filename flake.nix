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
