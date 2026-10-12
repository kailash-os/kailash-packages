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

          # ---- KA-08.4 torch Shape 4 gate (kailash-os#108) ----------------
          # Shape 4 (plan §5.3/D6): NON-GPU pytorch default + an explicit
          # -nvidia variant built only by labelled jobs, never pulled by
          # default. No global cudaSupport flip anywhere (D6) — the
          # variant arg lives inside pkgs/torch-nvidia/default.nix.
          #
          # Mechanic (probed locally at pin e7439b6b, darwin sandbox and
          # hosted-equivalent): the legs bake the torch .drv PATH into an
          # env var — build-time context mounts that drv's whole closure
          # graph — and a python dep-walk counts cuda-family input
          # derivations (`cuda|cudnn|cusparselt|cutensor|nccl|cudatoolkit`
          # on the drv basename, case-insensitive). A missing closure file
          # fails the scan (an incomplete walk proves nothing). Bare
          # `nvidia` is deliberately NOT a cuda-family token: the
          # cpu-default torch closure's only nvidia-token drv is triton's
          # own upstream 0002-nvidia-driver-short-circuit-before-ldconfig
          # patch (a CPU-build patch shipped by the triton recipe), not a
          # CUDA library.
          #
          # Probe scope: the leg evals pkgs/pytorch/default.nix itself
          # against an allowUnfree-scoped nixpkgs so the CUDA-carrying
          # RED stub evaluates; the dep scan is the gate here — licensing
          # of the DEFAULT surface stays the flake surfaces' job.
          torch-cpu-shape = pkgs.runCommand "torch-cpu-shape"
            {
              nativeBuildInputs = [ pkgs.python3 ];
              env.SHAPE_MODE = "cpu";
              env.TORCH_DRV =
                (import (self + "/pkgs/pytorch/default.nix") {
                  inherit lib;
                  python3Packages = (import inputs.nixpkgs {
                    inherit system;
                    config.allowUnfree = true;
                  }).python3Packages;
                }).drvPath;
              env.PACKAGE_EXPORTED = lib.boolToString (self.packages.${system} ? "pytorch");
            }
            ''
            python3 - <<'PY'
import json, os, re, sys
from collections import deque

drv_re = re.compile(r"/nix/store/[a-z0-9]{32}-[a-zA-Z0-9._%+-]+\.drv")
cu_re = re.compile(r"cuda|cudnn|cusparselt|cutensor|nccl|cudatoolkit", re.I)

root = os.environ["TORCH_DRV"]
mode = os.environ["SHAPE_MODE"]
seen = set()
q = deque([root])
misses = []
while q:
    p = q.popleft()
    if p in seen:
        continue
    seen.add(p)
    try:
        with open(p, "r", errors="replace") as fh:
            txt = fh.read()
    except OSError:
        misses.append(p)
        continue
    for m in drv_re.findall(txt):
        if m not in seen:
            q.append(m)

hits = sorted(t for t in seen if cu_re.search(t.rsplit("/", 1)[-1]))
print(json.dumps({
    "root": root,
    "mode": mode,
    "closure_drvs": len(seen),
    "misses": len(misses),
    "cuda_family_hits": len(hits),
}, indent=1))
for t in hits[:10]:
    print("  cuda-family drv:", t)
if misses:
    print("MISSING from mounted closure (%d), e.g. %s — incomplete scan proves nothing"
          % (len(misses), misses[:3]))
    sys.exit(1)
if mode == "cpu":
    if hits:
        print("torch-cpu-shape: FAIL — the default torch closure carries %d "
              "cuda-family input derivations; Shape 4 requires a cuda-free "
              "non-GPU default" % len(hits))
        sys.exit(1)
    print("torch-cpu-shape: scan OK — %d-drv closure carries ZERO cuda-family "
          "input derivations" % len(seen))
else:
    if not hits:
        print("torch-nvidia-shape: FAIL — the -nvidia variant closure carries "
              "NO cuda-family deps (it is not the explicit CUDA variant)")
        sys.exit(1)
    print("torch-nvidia-shape: scan OK — %d-drv closure carries %d cuda-family "
          "input derivations" % (len(seen), len(hits)))
PY
            if [ "$PACKAGE_EXPORTED" != "true" ]; then
              echo "torch-cpu-shape: FAIL — packages.${system}.pytorch is not "
                   "exported (.nocall still present? the non-GPU default must "
                   "ship the default packages/matrix surface)"
              exit 1
            fi
            echo "torch-cpu-shape: OK — non-GPU default exported"
            touch $out
          '';

          # Shape-4 variant leg: the explicit -nvidia output must EXIST,
          # carry CUDA deps, stay OUT of the default auto-call surface
          # (.nocall — never pulled by default, labelled-CI-built only)
          # and differ from the default torch drv. RED: the file is
          # absent → the leg refuses loudly.
          torch-nvidia-shape = pkgs.runCommand "torch-nvidia-shape"
            {
              nativeBuildInputs = [ pkgs.python3 ];
              env.SHAPE_MODE = "nvidia";
              env.VARIANT_FILE = lib.boolToString
                (builtins.pathExists (self + "/pkgs/torch-nvidia/default.nix"));
              env.VARIANT_DRV =
                if builtins.pathExists (self + "/pkgs/torch-nvidia/default.nix")
                then (import (self + "/pkgs/torch-nvidia/default.nix") {
                  inherit lib;
                  python3Packages = (import inputs.nixpkgs {
                    inherit system;
                    config.allowUnfree = true;
                  }).python3Packages;
                }).drvPath
                else "";
              env.DEFAULT_DRV =
                (import (self + "/pkgs/pytorch/default.nix") {
                  inherit lib;
                  python3Packages = (import inputs.nixpkgs {
                    inherit system;
                    config.allowUnfree = true;
                  }).python3Packages;
                }).drvPath;
              env.NOCALL_PRESENT = lib.boolToString
                (builtins.pathExists (self + "/pkgs/torch-nvidia/.nocall"));
            }
            ''
            if [ "$VARIANT_FILE" != "true" ]; then
              echo "torch-nvidia-shape: FAIL — pkgs/torch-nvidia/default.nix "
                   "does not exist: the explicit -nvidia variant output is "
                   "not landed (Shape 4: non-GPU default + explicit variant)"
              exit 1
            fi
            if [ "$NOCALL_PRESENT" != "true" ]; then
              echo "torch-nvidia-shape: FAIL — pkgs/torch-nvidia/.nocall is "
                   "missing: the variant must stay OUT of the auto-call "
                   "packages/build-matrix default surface (never pulled by "
                   "default; labelled CI jobs build it explicitly)"
              exit 1
            fi
            if [ "$VARIANT_DRV" = "$DEFAULT_DRV" ]; then
              echo "torch-nvidia-shape: FAIL — the -nvidia variant drv equals "
                   "the default torch drv ($VARIANT_DRV): the variant is not "
                   "a distinct CUDA shape"
              exit 1
            fi
            python3 - <<'PY'
import json, os, re, sys
from collections import deque

drv_re = re.compile(r"/nix/store/[a-z0-9]{32}-[a-zA-Z0-9._%+-]+\.drv")
cu_re = re.compile(r"cuda|cudnn|cusparselt|cutensor|nccl|cudatoolkit", re.I)

root = os.environ["VARIANT_DRV"]
seen = set()
q = deque([root])
misses = []
while q:
    p = q.popleft()
    if p in seen:
        continue
    seen.add(p)
    try:
        with open(p, "r", errors="replace") as fh:
            txt = fh.read()
    except OSError:
        misses.append(p)
        continue
    for m in drv_re.findall(txt):
        if m not in seen:
            q.append(m)

hits = sorted(t for t in seen if cu_re.search(t.rsplit("/", 1)[-1]))
print(json.dumps({
    "root": root,
    "closure_drvs": len(seen),
    "misses": len(misses),
    "cuda_family_hits": len(hits),
}, indent=1))
for t in hits[:10]:
    print("  cuda-family drv:", t)
if misses:
    print("MISSING from mounted closure (%d), e.g. %s — incomplete scan proves nothing"
          % (len(misses), misses[:3]))
    sys.exit(1)
if not hits:
    print("torch-nvidia-shape: FAIL — the -nvidia variant closure carries NO "
          "cuda-family deps (it is not the explicit CUDA variant)")
    sys.exit(1)
print("torch-nvidia-shape: OK — %d-drv variant closure carries %d cuda-family "
      "input derivations; distinct from the default drv" % (len(seen), len(hits)))
PY
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
      # Documented fallback (plan §5.3): if the nixpkgs variant fights
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
