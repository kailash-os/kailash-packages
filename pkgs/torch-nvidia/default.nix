# torch-nvidia — the EXPLICIT CUDA (NVIDIA) variant of the PyTorch family
# (KA-08.4 [child of KA-08], Shape 4 / D6, kailash-os#108).
#
# GREEN commit of the watched-RED chain. This is the `torch.override
# { cudaSupport = true; }` build (the nixpkgs torchWithCuda contract):
# its recursive closure carries 49 cuda-family input derivations at the
# pin (cuda_cudart, libcublas, libcusolver, cudnn 9.22, nvcc,
# nvdisasm, cusparse_lt, nvshmem, … — probed on both lane systems, x86
# 3768-drv / arm 3382-drv closures). A CUDA-carrying derivation, never
# built by the default surface:
#
#   * `.nocall` beside this file EXCLUDES it from the auto-call
#     (pkgs/auto-call.nix) — packages.<system>.torch-nvidia does NOT
#     exist, the build-matrix adapter drops it, and no default consumer
#     can pull it. The variant is ONLY built by labelled CI jobs, on
#     demand, against an allowUnfree-scoped nixpkgs — the command is
#     documented in flake.nix's Shape-4 block.
#   * the checks.*.torch-nvidia-shape leg (torch-shape-eval-proofs)
#     asserts: file present, .nocall present, NOT in the packages
#     surface, outPath distinct from the default torch's, and
#     passthru.cudaSupport == true (the CUDA-flagged contract).
#   * the default pull of this repo must never touch it:
#     overlays.default + packages.<system> stay torch-(cpu)-only.
#
# pname override: the drv distinguishes itself (`torch-nvidia`) while
# inheriting torch's version and passthru contract.
#
# Documented fallback (plan §5.3): if the nixpkgs variant fights
# (breakage or licence churn), the nixvital/ml-pkgs torch-family
# overlay is the designated fallback source for this variant line —
# compose it at the flake's §4.4 optional-inputs seam; the default
# pytorch line stays nixpkgs-native.
{
  lib,
  python3Packages,
}:

(python3Packages.torch.override {
  # the explicit CUDA variant (torchWithCuda contract); rocm stays off —
  # a separate variant if the roadmap ever asks (Shape 4 is NVIDIA-only)
  cudaSupport = true;
  rocmSupport = false;
}).overrideAttrs (old: {
  pname = "torch-nvidia";
  meta = (old.meta or { }) // {
    description = "PyTorch — the explicit CUDA (NVIDIA GPU) variant of the Kailash torch family (labelled-CI-built; never pulled by default)";
  };
})
