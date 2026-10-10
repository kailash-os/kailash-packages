"""Loader for the two Kailash manifest files (KA-14.1, plan §7.1).

Resolves manifest/categories.yaml + manifest/tools.yaml relative to this
module, which holds in the repo tree, in the flake source tree (src = self)
and installed — where `cli/kailash/__file__` always sits beside a sibling
`../../manifest` because the derivation consumes the repo's cli/ subtree
wholesale (§7.3 bakes the same tree). Installed-in-place deployments that
split the manifest from the package can override both locations through
KAILASH_MANIFEST (KAILASH_CATEGORIES accepted as the §7.3 spelling).

Data accessors only: this module parses and hands rows back. The manifest
invariants stay single-homed in tests/validate_manifest.py (AGENTS.md
single-home rule) — the CLI never re-implements them.
"""
import os

try:
    import yaml
except ImportError:  # pragma: no cover - reported by main(), not raised
    yaml = None

__all__ = [
    "ManifestError",
    "categories_path",
    "tools_path",
    "load_categories",
    "load_tools",
]

# tools.yaml packaging.status vocabulary (§5.2) — the `kailash list
# --status` filter choices.
STATUSES = ("native", "stale", "bespoke", "module", "data")


class ManifestError(Exception):
    """Manifest unreadable, unparsable, or structurally not a manifest."""


def categories_path():
    """categories.yaml next to the package: <pkg>/../../manifest/categories.yaml.

    Resolves in the repo (cli/kailash -> ../../manifest), in the flake
    source tree (src = self; same relative layout), and installed (the
    wheel ships the whole cli/ tree). KAILASH_MANIFEST overrides — §7.3's
    env spelling, honoured for installed deployments that move the data.
    """
    override = os.environ.get("KAILASH_MANIFEST")
    if override:
        return os.path.join(override, "categories.yaml")
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, os.pardir, os.pardir, "manifest", "categories.yaml")


def tools_path():
    """tools.yaml — the same base directory as categories_path()."""
    override = os.environ.get("KAILASH_MANIFEST")
    if override:
        return os.path.join(override, "tools.yaml")
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, os.pardir, os.pardir, "manifest", "tools.yaml")


def _load(path, key):
    """Parse one manifest file and return its top-level <key> list."""
    if yaml is None:
        raise ManifestError("pyyaml unavailable: manifest cannot be parsed")
    try:
        with open(path) as f:
            doc = yaml.safe_load(f)
    except FileNotFoundError:
        raise ManifestError("manifest not readable: %s" % path)
    except yaml.YAMLError as exc:
        raise ManifestError("manifest not parseable: %s: %s" % (path, exc))
    if not isinstance(doc, dict) or not isinstance(doc.get(key), list):
        raise ManifestError(
            "manifest malformed: %s carries no top-level '%s' list" % (path, key)
        )
    return doc[key]


def load_categories():
    """Category rows from categories.yaml (KA-14 data source).

    Structural invariants (unique ids, required fields, census totals)
    stay in tests/validate_manifest.py — the validator is the single
    enforcement point; this loader is not a second gate.
    """
    return _load(categories_path(), "categories")


def load_tools():
    """Tool rows from tools.yaml (empty while the header-only stub stands)."""
    return _load(tools_path(), "tools")
