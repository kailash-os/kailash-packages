# kailash-mcp — the distro's own MCP server, generated from the manifest
# (KA-25, kailash-os#25; plan §3.5 O-7, §11.2).
#
# FIRST-PARTY: no upstream pin — the source is this repository's cli/
# subtree, exactly like pkgs/kailash (KA-14.1/14.2). The server face is
# the extra-dependency install of the SAME wheel: cli/kailash/
# mcp_server.py (the MCP stdio server over the kailash.manifest loader)
# + the kailash-mcp entry point (cli/pyproject.toml [project.scripts]).
# "Generated from the manifest" is the loader contract: the server
# serves manifest/tools.yaml + categories.yaml through kailash.manifest
# — the manifest files are derivation INPUTS (baked env paths, the same
# §7.3 drift-killer as the CLI derivation) and the MCP tools never
# hardcode a row.
#
# GRANT POSTURE (KA-25 v1, plan §11.2): the read-only MCP tools
# (list/search/info/grant_status) serve any unsupervised agent;
# kailash_run_tool is deny-by-default and routes through the
# KAILASH_GRANTS state (the OS side's modules/base/agent-grants.nix
# mints /etc/kailash/grants/grants.json into the closure; grant-scoped
# actions append JSON lines to KAILASH_GRANT_LOG). Exp-class manifest
# rows additionally require the grant's allow_exp — and the exec
# transport stays behind the host's lab-mode double-key gate by
# construction (never a bypass of the §11.2 gate).
{
  lib,
  python3Packages,
  makeBinaryWrapper,
}:

python3Packages.buildPythonApplication {
  pname = "kailash-mcp";
  version = "0.1.0";
  pyproject = true;

  # the first-party tool dir at the repo root (cli/), consumed wholesale
  src = ../../cli;

  build-system = with python3Packages; [ setuptools ];

  # the wheel's [mcp] extra: the MCP SDK (python3Packages.mcp 1.29.0 at
  # the pin, probed) + the CLI's own pyyaml
  dependencies = with python3Packages; [ mcp pyyaml ];

  # §7.3 the drift killer (same contract as pkgs/kailash): the manifest
  # files are derivation inputs; the wrapper bakes their store paths
  manifestTools = ../../manifest/tools.yaml;
  manifestCategories = ../../manifest/categories.yaml;

  nativeBuildInputs = [ makeBinaryWrapper ];

  pythonImportsCheck = [
    "kailash"
    "kailash.manifest"
    "kailash.cli"
    "kailash.mcp_server"
  ];

  doCheck = false;

  postFixup = ''
    wrapProgram $out/bin/kailash-mcp \
      --prefix KAILASH_MANIFEST : $manifestTools \
      --prefix KAILASH_CATEGORIES : $manifestCategories
  '';

  meta = {
    description = "kailash-mcp — the distro's own MCP server, generated from the manifest (KA-25)";
    license = lib.licenses.bsd3;
    mainProgram = "kailash-mcp";
  };
}
