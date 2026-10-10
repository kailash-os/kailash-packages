# dnsrecon — pinned from master (nvfetcher/_sources; KA-02.3 #68).
# Shape 1 (pure python, plan §5.3): buildPythonApplication over the
# committed pin; doCheck = false (tests hit live DNS) with
# pythonImportsCheck as the smoke gate (harness-before-capability).
# Recipe lineage: nixpkgs pkgs/by-name/dn/dnsrecon, rebuilt against the
# overlay pin (the census marks c-01 nixpkgs-stale — this is the
# overlay-currency path). Pinned rev 13c47504: master @ 2026-10-09.
{
  lib,
  callPackage,
  python3,
}:

let
  sources = callPackage ../../nvfetcher/_sources/generated.nix { };
in
python3.pkgs.buildPythonApplication (finalAttrs: {
  pname = "dnsrecon";
  version = "1.6.4-unstable-2026-10-09";
  pyproject = true;

  src = sources.dnsrecon.src;

  postPatch = ''
    substituteInPlace pyproject.toml \
      --replace-fail "setuptools>=82.0.1" "setuptools"
  '';

  pythonRelaxDeps = true;

  build-system = with python3.pkgs; [ setuptools ];

  dependencies = with python3.pkgs; [
    dnspython
    loguru
    httpx
    fastapi
    uvicorn
    slowapi
    stamina
    ujson
    lxml
    netaddr
    requests
    setuptools
  ];

  # tests require live DNS (access to /etc/resolv.conf) — the build
  # sandbox has neither; imports are the smoke gate
  doCheck = false;

  pythonImportsCheck = [ "dnsrecon" ];

  meta = {
    description = "DNS enumeration, wildcard resolution, and zone-transfer tool";
    homepage = "https://github.com/darkoperator/dnsrecon";
    changelog = "https://github.com/darkoperator/dnsrecon/commits/${sources.dnsrecon.version}";
    license = lib.licenses.gpl2Only;
    mainProgram = "dnsrecon";
  };
})
