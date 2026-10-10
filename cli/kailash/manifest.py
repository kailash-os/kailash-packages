"""Loader for the two Kailash manifest files (KA-14.1, plan §7.1).

Per-file env overrides per the §7.3 bake contract (KA-14.2):
KAILASH_MANIFEST names the tools.yaml FILE and KAILASH_CATEGORIES the
categories.yaml FILE — two independent paths, exactly what the
wrapProgram bake assigns in pkgs/kailash (the manifest and categories
source files are derivation inputs, so the manifest content is inside
the CLI's derivation hash and `kailash list` cannot disagree with the
installed system). The values name FILES, not directories: a
per-file bake with the tools list pointing at file A and categories at
file B resolves only when the two vars are read independently. Both
unset, resolution falls back to `__file__`-relative paths beside the
package (repo tree, flake source tree with src = self, and installed —
each holds the sibling `../../manifest` layout), which stays the
default for every deployment that keeps the repo's cli/ + manifest/
subtree together.

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
    """categories.yaml — the FILE KAILASH_CATEGORIES names (§7.3 bake).

    Override values name the file itself, never a directory: the
    wrapper bakes one store path per manifest file. Unset, the file
    resolves __file__-relative (<pkg>/../../manifest/categories.yaml),
    which holds in the repo (cli/kailash -> ../../manifest), in the
    flake source tree (src = self; same relative layout), and installed
    (the package ships the whole cli/ subtree).
    """
    override = os.environ.get("KAILASH_CATEGORIES")
    if override:
        return override
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, os.pardir, os.pardir, "manifest", "categories.yaml")


def tools_path():
    """tools.yaml — the FILE KAILASH_MANIFEST names (§7.3 bake).

    The same per-file contract as categories_path(): an override value
    is the tools.yaml file itself, independent of KAILASH_CATEGORIES.
    """
    override = os.environ.get("KAILASH_MANIFEST")
    if override:
        return override
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, os.pardir, os.pardir, "manifest", "tools.yaml")


def _load(path, key):
    """Parse one manifest file and return its top-level <key> list."""
    if yaml is None:
        raise ManifestError("pyyaml unavailable: manifest cannot be parsed")
    try:
        with open(path) as f:
            doc = yaml.safe_load(f)
    except OSError:
        # unreadable, absent, or not-a-file (a directory named by an
        # env override included) — a manifest file the CLI cannot open
        # is an exit-2 error path, never a traceback
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
