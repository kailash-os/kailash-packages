# picklescan — mmaitre314/picklescan, the static security scanner for
# pickle/PyTorch model files (KA-22, kailash-os#22; A-4 model supply
# chain; plan §9 Phase 5). Shape 1 (§5.3): buildPythonApplication over
# the committed nvfetcher pin; setuptools backend (setup.cfg metadata,
# version 1.0.5 at the pin), zero runtime deps beyond the stdlib
# (install_requires is EMPTY upstream — verified at the pin), so the
# smoke gate is pythonImportsCheck ["picklescan"] + an install-time
# `picklescan --help`.
#
# Pin: main head 5e7ab22cb5bc59c4276820df5153829db4c751e8 (2026-09-01,
# verified via the GitHub API before committing). MIT (setup.cfg
# classifier + LICENSE at the pin).
{
  lib,
  callPackage,
  python3,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };
in

python3.pkgs.buildPythonApplication {
  pname = "picklescan";
  # setup.cfg version at the pin + pin date from _sources.picklescan.date
  version = "1.0.5-unstable-2026-09-01";

  src = sources.picklescan.src;
  pyproject = true;

  build-system = with python3.pkgs; [ setuptools ];

  # upstream install_requires is EMPTY (setup.cfg at the pin, verified) —
  # the scanner is stdlib-only by design

  doCheck = false;

  pythonImportsCheck = [ "picklescan" ];

  doInstallCheck = true;
  postInstall = ''
    $out/bin/picklescan --help
  '';

  meta = {
    description = "Security scanner detecting Python Pickle files performing suspicious actions";
    homepage = "https://github.com/mmaitre314/picklescan";
    changelog = "https://github.com/mmaitre314/picklescan/releases";
    license = lib.licenses.mit;
    mainProgram = "picklescan";
  };
}
