# mcp-guardian — EqtyLab's MCP Guardian, the proxy/guard layer for
# exercising MCP server controls (KA-22, kailash-os#22; A-3 agentic/MCP
# tool-use; plan §9 Phase 5). Shape 4-adjacent (Rust workspace, §5.3):
# buildRustPackage over the committed nvfetcher pin with the workspace
# Cargo.lock as the lock pin (hash pinned, cargo-vendor hook).
#
# WORKSPACE SCOPING (verified at the pin): mcp-guardian is a Tauri
# desktop app + three sibling crates (mcp-guardian-core, -cli, -proxy).
# The manifest row wants the OPERABLE surface — the CLI + proxy crates
# — not the Tauri desktop bundle (a GUI app needs the whole webkit
# toolchain; the proxy + CLI are the headless guard layer the manifest
# description names: "proxy and guard layer for MCP server controls").
# Upstream's own flake builds the desktop bundle; this derivation
# builds the three non-Tauri workspace members via cargo lock
# inheritance (buildRustPackage with a Cargo.lock that inherits the
# pinned workspace lock SHA — the workspace lock at the pin is
# committed upstream).
#
# Pin: main head 54395bfe65c8db7192d62a6e6ecab246f818193f (2025-04-10,
# verified via the GitHub API before committing — upstream is slow; the
# census pins reference posture per R7). Apache-2.0 (LICENSE at the
# pin).
{
  lib,
  callPackage,
  rustPlatform,
  pkg-config,
  openssl,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };
in

rustPlatform.buildRustPackage {
  pname = "mcp-guardian";
  # workspace patch version is not tracked in Cargo.toml (0-unstable
  # pin form); pin date from _sources.mcp-guardian.date
  version = "0-unstable-2025-04-10";

  src = sources.mcp-guardian.src;

  # The workspace Cargo.lock pinned IN-TREE (byte-identical with the pin's
  # lock — checked by the pkgs flake's ka22 guard leg): a src-embedded
  # lockFile forces the source FOD's realization at EVAL (nix flake check
  # --no-build refuses: "path is not valid") — the committed copy keeps
  # the check pure.
  cargoLock = {
    lockFile = ./Cargo.lock;
  };

  # Skip the tauri workspace member (GUI bundle, out of scope — the
  # guard layer is the core/cli/proxy triad)
  postPatch = ''
    substituteInPlace Cargo.toml --replace-fail '    "mcp-guardian/src-tauri",' ""
  '';

  nativeBuildInputs = [ rustPlatform.cargoSetupHook pkg-config ];
  buildInputs = [ openssl ];

  doCheck = false;

  meta = {
    description = "MCP Guardian — proxy and guard layer for exercising MCP server controls (allow-lists, ratelimits)";
    homepage = "https://github.com/eqtylab/mcp-guardian";
    changelog = "https://github.com/eqtylab/mcp-guardian/commits/${sources.mcp-guardian.version}";
    license = lib.licenses.asl20;
    mainProgram = "mcp-guardian-cli";
  };
}
