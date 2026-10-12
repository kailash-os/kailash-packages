# pytorch — PyTorch (manifest id: pytorch; KA-08.4 [child of KA-08], Shape 4
# — non-GPU default + explicit -nvidia variant, D6).
#
# The NON-GPU DEFAULT of the Kailash torch family (GREEN commit of the
# watched-RED chain): an explicit `cudaSupport = false` build of the
# nixpkgs torch — the plain `python3Packages.torch` evaluated at this
# pin already defaults to cudaSupport = false, but the default is
# overridden EXPLICITLY here so the non-GPU shape survives a future
# upstream default flip (D6: never a global cudaSupport bool; the
# cudaSupport arg stays inside this derivation).
#
# Acceptance (kailash-os#108): "non-GPU torch default builds without
# CUDA deps". Build-time evidence probed at pin e7439b6b (nix
# derivation show -r, both lane systems): the cudaSupport=false build's
# recursive closure carries ZERO cuda-family input derivations (2844
# drvs on x86_64-linux / 2459 on aarch64-linux; the same scan over the
# torchWithCuda closure counts 49 cuda-family drvs on both). The
# eval-time gate (checks.*.torch-shape-eval-proofs) asserts the
# passthru contract (cudaSupport/rocmSupport = false,
# cudaCapabilities = [ ]) on every flake check.
#
# Passthrough (NOT overrideAttrs-rewrapped): the outPath equals the
# plain nixpkgs default-torch output at this pin, so the hosted build
# leg PULLS the cached cpu-only torch from cache.nixos.org instead of
# rebuilding a multi-hour big-parallel derivation. The passthru
# contract (what the eval gate asserts) is torch's own, untouched.
#
# The explicit -nvidia variant lives in pkgs/torch-nvidia/default.nix
# (.nocall-excluded from this default surface — never pulled by
# default; labelled CI jobs build it). Documented fallback if the
# nixpkgs variant fights: the nixvital/ml-pkgs torch-family overlay
# (plan §5.3; the seam is documented in flake.nix).
{
  lib,
  python3Packages,
}:

python3Packages.torch.override {
  # Shape 4 (D6): the non-GPU default is cudaSupport = false EXPLICITLY,
  # not by nixpkgs-default drift.
  cudaSupport = false;
  rocmSupport = false;
}
