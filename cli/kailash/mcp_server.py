"""kailash-mcp — the distro's own MCP server, generated from the manifest
(KA-25, kailash-os#25; plan §3.5 O-7, §11.2).

First-party module of the kailash CLI package (the same cli/ source tree
pkgs/kailash builds): an MCP stdio server whose tools serve the two
manifest files through the same loader (`kailash.manifest`) the CLI uses
— the manifest is the only registry, the server never hardcodes a row.

CAPABILITY-GRANT POSTURE (plan §11.2, the KA-25 v1 grant design):
  * ALWAYS available (read-only, safe for unsupervised agents):
      - kailash_list_tools      — manifest rows with per-category filters
      - kailash_search_tools    — substring/field search
      - kailash_tool_info       — one full row by id
      - kailash_grant_status    — the live grant state for THIS session
  * GRANT-GATED (default DENY):
      - kailash_run_tool        — execute a manifest tool. Refuses unless
        KAILASH_GRANTS names a live grant whose window covers now, whose
        categories cover the tool's primary (or the tool is explicitly
        listed), and whose allow_exp covers safety.level == "exp" tools.
        Every invocation — allowed OR refused — appends one JSON line to
        the grant action log (KAILASH_GRANT_LOG), so grant-scoped actions
        are logged (plan §11.2).

Unset KAILASH_GRANTS ⇒ no grants exist ⇒ kailash_run_tool always
refuses (deny-by-default; unsupervised agents keep list/search/read
only — the four read-only tools above never carry tool-level side
effects). The OS side (modules/base/agent-grants.nix) mints the grants
file into the closure; an operator edits/replaces it to extend.
"""
import json
import os
import sys
from datetime import datetime, timezone

from . import manifest

PROG = "kailash-mcp"


def _fail(msg):
    sys.stderr.write("%s: %s\n" % (PROG, msg))


def _grants_doc():
    """Parsed grants doc ({} when no grants file resolves). Never raises:
    a malformed grants file is a deny + a note — the posture stays
    deny-by-default even when the state file is broken."""
    path = os.environ.get("KAILASH_GRANTS")
    if not path:
        return {}
    try:
        with open(path) as f:
            doc = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(doc, dict):
        return {}
    return doc


def _grant_log_path():
    return os.environ.get("KAILASH_GRANT_LOG") or ""


def _log_action(event):
    """Append one JSON line per grant-scoped action (the §11.2 log)."""
    path = _grant_log_path()
    if not path:
        return
    line = json.dumps(dict(event, ts=datetime.now(timezone.utc).isoformat()),
                      sort_keys=True)
    try:
        with open(path, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _parse_ts(s):
    """ISO-8601 → aware UTC datetime, or None (absent/unparsable)."""
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except ValueError:
        return None


def _live_grants(tool_row=None, action="exec"):
    """The grants from the doc that are live for <action> on <tool_row>.

    Window: not_before <= now <= not_after (a missing bound fails OPEN
    only toward denial — an absent not_after NEVER means unlimited v1;
    every minted grant carries both bounds, enforced here).
    """
    now = datetime.now(timezone.utc)
    live = []
    for holder, grant in (_grants_doc().get("grants") or {}).items():
        if not isinstance(grant, dict):
            continue
        start = _parse_ts(grant.get("not_before"))
        end = _parse_ts(grant.get("not_after"))
        if end is None or end < now:
            continue  # no/window-closed expiry ⇒ not live (deny-by-default)
        if start is not None and start > now:
            continue
        if action == "exec":
            cats = grant.get("categories") or []
            listed = grant.get("tools") or []
            tool_id = tool_row.get("id") if tool_row else None
            tool_cat = tool_row.get("category") if tool_row else None
            if tool_cat and tool_cat not in cats and tool_id not in listed:
                continue
            if tool_row and (tool_row.get("safety") or {}).get("level") == "exp" \
                    and not grant.get("allow_exp"):
                continue
        live.append({"holder": holder, "grant": grant})
    return live


def _row_public(row):
    """The read-only projection of one manifest row."""
    return {
        "id": row.get("id"),
        "name": row.get("name"),
        "layer": row.get("layer"),
        "category": row.get("category"),
        "description": row.get("description"),
        "license": row.get("license"),
        "packaging_status": (row.get("packaging") or {}).get("status"),
        "safety_level": (row.get("safety") or {}).get("level"),
    }


def _rows():
    try:
        return manifest.load_tools()
    except manifest.ManifestError as exc:
        _fail(str(exc))
        return []


def build_server():
    from mcp.server.fastmcp import FastMCP

    m = FastMCP("kailash-mcp")

    @m.tool()
    def kailash_list_tools(layer: str = "", category: str = "",
                           status: str = "") -> str:
        """List Kailash manifest tool rows (read-only). Optional filters:
        layer (CLASSIC/ATTACK/DEFENCE/OPS), category (census id prefix or
        full id), status (native/stale/bespoke/module/data)."""
        rows = _rows()
        if layer:
            rows = [r for r in rows if r.get("layer") == layer]
        if category:
            rows = [r for r in rows
                    if str(r.get("category", "")).startswith(category)]
        if status:
            rows = [r for r in rows
                    if (r.get("packaging") or {}).get("status") == status]
        return json.dumps([_row_public(r) for r in rows], sort_keys=True)

    @m.tool()
    def kailash_search_tools(query: str, limit: int = 25) -> str:
        """Search Kailash manifest tool rows (read-only):
        case-insensitive substring across id, name, description."""
        q = (query or "").lower()
        out = []
        for r in _rows():
            hay = " ".join(filter(None, [
                r.get("id"), r.get("name"), r.get("description")])).lower()
            if q in hay:
                out.append(_row_public(r))
            if len(out) >= max(1, int(limit)):
                break
        return json.dumps(out, sort_keys=True)

    @m.tool()
    def kailash_tool_info(tool_id: str) -> str:
        """One Kailash manifest tool row, full form (read-only)."""
        for r in _rows():
            if r.get("id") == tool_id:
                return json.dumps(r, sort_keys=True)
        return json.dumps({"error": "absent tool id", "tool_id": tool_id})

    @m.tool()
    def kailash_grant_status() -> str:
        """The live grants for this session (read-only): holders, their
        category scope, exp posture, windows — no secrets."""
        live = _live_grants()
        return json.dumps({
            "grants_file": bool(os.environ.get("KAILASH_GRANTS")),
            "live": [{"holder": g["holder"],
                      "categories": g["grant"].get("categories") or [],
                      "allow_exp": bool(g["grant"].get("allow_exp")),
                      "allow_service_start":
                          bool(g["grant"].get("allow_service_start")),
                      "not_before": g["grant"].get("not_before"),
                      "not_after": g["grant"].get("not_after")}
                     for g in live],
        }, sort_keys=True)

    @m.tool()
    def kailash_run_tool(tool_id: str) -> str:
        """GRANT-GATED: run a manifest tool through the lab gate posture.
        Denies unless a live grant covers the tool (category scope, exp
        posture). Every call — allowed or refused — is logged."""
        rows = _rows()
        row = next((r for r in rows if r.get("id") == tool_id), None)
        event = {"action": "kailash_run_tool", "tool": tool_id}
        if row is None:
            _log_action(dict(event, decision="refused", reason="absent-id"))
            return json.dumps({"error": "absent tool id", "tool_id": tool_id})
        live = _live_grants(row, "exec")
        if not live:
            _log_action(dict(event, decision="refused",
                             reason="no-live-grant"))
            return json.dumps({
                "error": "refused: no live grant covers this tool",
                "tool_id": tool_id,
                "grant_required": True,
            })
        _log_action(dict(event, decision="allowed",
                         holder=live[0]["holder"]))
        return json.dumps({
            "error": "not-executable-in-v1",
            "tool_id": tool_id,
            "note": ("grant v1 scopes and logs; execution routes through "
                     "the host's lab-mode gate (KAILASH_LAB_MODE "
                     "double-key) in the wave that lands the exec "
                     "transport — plan §11.2"),
            "holder": live[0]["holder"],
        })

    return m


def main():
    m = build_server()
    m.run()


if __name__ == "__main__":
    main()
