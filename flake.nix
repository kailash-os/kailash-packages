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
          manifest-wellformed = pkgs.runCommand "manifest-wellformed"
            {
              nativeBuildInputs = [ pkgs.python3 ];
            } ''
            # lenient until the real manifest lands (KA-04/KA-05):
            # both files must exist and parse as YAML.
            python3 ${./tests/validate_manifest.py}
            touch $out
          '';
        };
      };
    };
}
