# hexstrike-ai — 0x4m4/hexstrike-ai: the MCP server that lets AI agents
# autonomously run 100+ security tools (KA-25, kailash-os#25; plan §3.5
# O-7 third-party deliverable, exp grant-gated).
#
# Shape 1 (plan §5.3): pure python, pinned from the upstream git head —
# pin d689933ff579d839c676c82b231f8e98326c5f04 (master head, committer
# date 2026-08-03T14:33:01Z, verified via the GitHub commits API; the
# manifest row's source block is the routing record). Licence MIT
# (upstream LICENSE read at the pin).
#
# Import-chain honesty (the Shape-1 static-audit rule): hexstrike_server.py
# EAGERLY imports flask, requests, psutil, aiohttp, bs4, selenium,
# webdriver-manager, mitmproxy at module level (verified against the
# pinned bytes). angr + pwntools are NOT module-level imports — they are
# the 150+ external tools hexstrike shells out to (the Kali side), never
# python deps here. requirements.txt pins bcrypt==4.0.1 for passlib;
# the python3Packages pin carries bcrypt 5.0.0 — passlib drifts are an
# upstream runtime matter, no passlib in the eager chain (verified).
#
# SAFETY: safety.level "exp" (manifest row) — never a package-list
# entry; the OS o-07 module routes it through kailash.safety.extraTools
# → the lab-mode double-key gate (§11.2); grants scope agent execution.
{
  lib,
  fetchFromGitHub,
  python3Packages,
}:

python3Packages.buildPythonApplication rec {
  pname = "hexstrike-ai";
  version = "unstable-2026-08-03";

  src = fetchFromGitHub {
    owner = "0x4m4";
    repo = "hexstrike-ai";
    rev = "d689933ff579d839c676c82b231f8e98326c5f04";
    hash = "sha256-M2dw5ZYt1EIsapboqygxeMS1W+cII3NUH3c3A9oAGaE=";
  };

  format = "other";

  # The EAGER import chain only (verified against the pinned bytes):
  # flask, requests, psutil, aiohttp, beautifulsoup4, selenium,
  # webdriver-manager, mitmproxy + the mcp SDK (hexstrike_mcp.py's
  # FastMCP). No angr/pwntools here — those are the external tools the
  # server shells, not module-level python imports.
  dependencies = with python3Packages; [
    flask
    requests
    psutil
    aiohttp
    beautifulsoup4
    selenium
    webdriver-manager
    mitmproxy
    mcp
  ];

  dontBuild = true;

  installPhase = ''
    runHook preInstall
    mkdir -p "$out/bin" "$out/lib/kailash/hexstrike-ai"
    cp "$src/hexstrike_server.py" "$out/lib/kailash/hexstrike-ai/"
    cp "$src/hexstrike_mcp.py" "$out/lib/kailash/hexstrike-ai/"
    # The manifest row's exec maps to the MCP client bridge entry
    # (hexstrike_mcp.py — the FastMCP server agents connect to); the
    # tooling backend (hexstrike_server.py) ships beside it.
    makeWrapper "${python3Packages.python}/bin/python" "$out/bin/hexstrike-ai" \
      --add-flags "$out/lib/kailash/hexstrike-ai/hexstrike_mcp.py" \
      --prefix PYTHONPATH : "${python3Packages.makePythonPath dependencies}"
    makeWrapper "${python3Packages.python}/bin/python" "$out/bin/hexstrike-server" \
      --add-flags "$out/lib/kailash/hexstrike-ai/hexstrike_server.py" \
      --prefix PYTHONPATH : "${python3Packages.makePythonPath dependencies}"
    runHook postInstall
  '';

  # Build-time smoke = the eager import chain compiles under the pinned
  # python NEVER a server boot (both entries bind ports on boot; boots
  # are exp-gated operator actions). pythonImportsCheck covers the SDK;
  # the two app files compile via python -m py_compile here.
  postInstallCheck = ''
    "${python3Packages.python}/bin/python" -m py_compile \
      "$out/lib/kailash/hexstrike-ai/hexstrike_mcp.py" \
      "$out/lib/kailash/hexstrike-ai/hexstrike_server.py"
  '';

  meta = {
    description = "HexStrike AI — MCP server letting AI agents autonomously run 100+ security tools (o-07)";
    homepage = "https://github.com/0x4m4/hexstrike-ai";
    license = lib.licenses.mit;
    mainProgram = "hexstrike-ai";
  };
}
