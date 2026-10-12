# pytorch — PyTorch (manifest id: pytorch; KA-08.4 [child of KA-08], Shape 4
# — non-GPU default + explicit -nvidia variant, D6).
#
# WATCHED-RED STUB (KA-08.4): this RED commit deliberately exports the
# WRONG Shape-4 state — a passthrough of python3Packages.torchWithCuda,
# the CUDA-carrying build, as the default torch — so the torch-cpu-shape
# gate leg demonstrably bites: its closure dep-scan counts cuda-family
# input derivations and fails. The GREEN commit swaps the body to the
# cudaSupport=false build and lands pkgs/torch-nvidia.
#
# `.nocall` keeps this stub OUT of the packages/matrix surfaces during
# the RED phase: an exported `torch` here would resolve the CUDA
# closure's unfree EULA licences (cuda_cccl et al) in every flake
# surface that builds packages.x86_64-linux.*, failing those gates for
# the wrong reason — the stub must fail the SHAPE gate, never the
# licence gate. GREEN (the cudaSupport=false build) drops `.nocall` so
# the cpu-default torch ships in the build matrix like other native
# packages.
{
  lib,
  python3Packages,
}:

# The pre-Shape-4 wrong state: CUDA-carrying torch as the default.
python3Packages.torchWithCuda
