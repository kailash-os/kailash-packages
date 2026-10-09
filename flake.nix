{
  description = "kailash-packages — the Kailash tool overlay: bespoke derivations + the tool manifest (independently consumable)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs = inputs@{ self, nixpkgs, flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = [ "x86_64-linux" "aarch64-linux" ];
      imports = [ ./flake-parts ];
      perSystem = { pkgs, system, ... }: {
        # packages auto-called per manifest (KA-02.3 wires the harness);
        # until then pkgs/ is empty and packages = {}
        packages = { };
        checks = {
          # runs the validator against the flake source tree (src = self) so
          # its relative manifest resolution holds in every context, with
          # pyyaml guaranteed via withPackages — the hosted-runner failure
          # (pyyaml absent, __file__-relative path in a filtered source copy)
          # is the proof the gate needs both. Lenient until the real manifest
          # lands (KA-02.2/KA-04/KA-05).
          manifest-wellformed = pkgs.runCommand "manifest-wellformed"
            {
              nativeBuildInputs = [ (pkgs.python3.withPackages (ps: [ ps.pyyaml ])) ];
              src = self;
            } ''
            python3 $src/tests/validate_manifest.py
            touch $out
          '';
        };
      };
    };
}
