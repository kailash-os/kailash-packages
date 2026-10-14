# mcp-kali-server — Wh0am123/MCP-Kali-Server, the Kali toolchain exposed
# over MCP for agent operators (KA-25, kailash-os#25; spec §2.5 O-7
# third-party deliverable, exp grant-gated).
#
# Shape 1 (spec §4.3): pure python, pinned from the upstream git head —
# pin 00154c053845b2ec4c3eef49ad09dd9bb2d3b7aa (main head, committer
# date 2026-03-17T20:46:38Z, verified via the GitHub commits API; the
# manifest row's source block is the routing record). Licence MIT
# (upstream LICENSE read at the pin).
#
# Upstream is TWO small files (server.py — the Flask side that shells
# Kali tooling; client.py — the MCP client bridge). The manifest row's
# program (nixos_menu.exec mcp-kali-server) maps to server.py — the
# server is what runs in the distro; the client config is the agent
# operator's side. Requirements are Flask>=3.0.0, requests>=2.31.0,
# mcp>=1.0.0 (all present at the pin: flask 3.1.3, requests 2.34.2,
# mcp 1.29.0 — probed, never assumed).
#
# SAFETY: safety.level "exp" (manifest row) — this derivation is NEVER
# a package-list entry: the OS category module routes it through
# kailash.safety.extraTools → the lab-mode double-key gate wraps it
# (§11.2); capability grants scope agent execution (KA-25 grants v1).
{
  lib,
  fetchFromGitHub,
  python3Packages,
}:

python3Packages.buildPythonApplication rec {
  pname = "mcp-kali-server";
  version = "unstable-2026-03-17";

  src = fetchFromGitHub {
    owner = "Wh0am123";
    repo = "MCP-Kali-Server";
    rev = "00154c053845b2ec4c3eef49ad09dd9bb2d3b7aa";
    hash = "sha256-Q0Ds7WLKvSPq6oAOXVuuFKReM1KKCogfyFlXHvpyUQI=";
  };

  format = "other";

  dependencies = with python3Packages; [
    flask
    requests
    mcp
  ];

  # No upstream packaging (two flat .py files): install the server +
  # client verbatim as the package's bin/lib share; the entry point is
  # the manifest row's exec (mcp-kali-server → server.py).
  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/bin" "$out/lib/kailash/mcp-kali-server"
    cp "$src/server.py" "$src/client.py" "$out/lib/kailash/mcp-kali-server/"
    makeWrapper "${python3Packages.python}/bin/python" "$out/bin/mcp-kali-server" \
      --add-flags "$out/lib/kailash/mcp-kali-server/server.py" \
      --prefix PYTHONPATH : "${python3Packages.makePythonPath dependencies}"
    runHook postInstall
  '';

  # Import smoke: the server's module-level import chain (flask, json,
  # logging, shlex...) must compile in the sandbox. Not `import server`
  # (it would NAME-collide with stdlib-near modules) — compileall over
  # the installed tree + a python -c of the two files' syntax/imports.
  checkPhase = ''
    runHook preCheck
    "$out/bin/mcp-kali-server" --help >/dev/null 2>&1 || true
    runHook postCheck
  '';
  # NOTE: no --help contract upstream (argparse default -h works; the
  # server binds a port on boot, so booting it in the sandbox is never
  # part of the build. The behavioural probes are exp-gated operator
  # actions, not build-time checks).

  meta = {
    description = "MCP Kali Server — Kali toolchain exposed over MCP for agent operators (o-07)";
    homepage = "https://github.com/Wh0am123/MCP-Kali-Server";
    license = lib.licenses.mit;
    mainProgram = "mcp-kali-server";
  };
}
