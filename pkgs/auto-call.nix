# The auto-call harness (KA-02.3 #68, plan §5.5).
#
# Every directory under pkgs/ is one tool whose derivation takes
# `pkg ` — the overlay-aware package set (the class in which nixpkgs
# staples resolve to nixpkgs' own, the overlay's to the overlay's, per
# the preference order native → pinned overlay → bespoke). A tool dir
# opts out of the auto-call with a `.nocall` marker (multi-output or
# non-package directories).
#
# The overlay exports it twice:
#   overlays.tools    — the callPackage overlay, composed by overlays.default
#   packages.<system> — flake-packages mirror (one entry per bespoke tool)
lib: (
  let
    # auto-call: one callPackage per pkgs/<dir>/default.nix
    callTools = pkg: dir: builtins.mapAttrs
      (name: _:
        pkg.callPackage (dir + "/${name}") { }
      )
      (lib.filterAttrs
        (n: ty: ty == "directory" && !builtins.pathExists (dir + "/${n}/.nocall"))
        (builtins.readDir dir));
  in
  callTools
)
