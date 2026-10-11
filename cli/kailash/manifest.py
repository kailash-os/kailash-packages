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

profiles.json (KA-17.2, kailash-os#115): the same per-file contract, third
var — KAILASH_PROFILES names a PROFILES.JSON file (the OS-side generator's
output, baked into the packaged binary's env like the two manifest files;
the OS follow-through lands the wrapProgram side). Unset, the file resolves
__file__-relative beside the package (<pkg>/../../../profiles/profiles.json
— the repo tree keeps a committed SAMPLE profiles/ so the self-test has
data; installed/flake-source trees built from the OS side carry the
generated file at the same layout or rely on the env). Absent everywhere →
`kailash profile list` exits 1 with a message naming KAILASH_PROFILES.
"""
import json
import os

try:
    import yaml
except ImportError:  # pragma: no cover - reported by main(), not raised
    yaml = None

__all__ = [
    "ManifestError",
    "categories_path",
    "tools_path",
    "profiles_path",
    "load_categories",
    "load_tools",
    "load_profiles",
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


def profiles_path():
    """profiles.json — the FILE KAILASH_PROFILES names (§7.3, KA-17.2).

    The per-file contract again, third var: an override value is the
    profiles.json file itself (the packaged binary bakes the store path
    the OS side pins). Unset, the file resolves __file__-relative
    (<pkg>/../../profiles/profiles.json — two levels up to the tree
    root, the same count the manifest fallback uses for manifest/;
    the committed sample lives there, and the OS-side generator lands
    its output at the same layout).

    Returns the path ONLY when the file actually exists: an env
    override naming an absent file (or an unset env without a fallback
    file) yields None — the caller (cmd_profile) turns None into the
    exit-1 diagnosis naming KAILASH_PROFILES, and load_profiles folds
    it into the empty list.
    """
    override = os.environ.get("KAILASH_PROFILES")
    if override:
        return override if os.path.isfile(override) else None
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(
        here, os.pardir, os.pardir, "profiles", "profiles.json")
    return candidate if os.path.isfile(candidate) else None


def load_profiles():
    """Profile rows from profiles.json (KA-17.2, kailash-os#115).

    Expected shape: {"profiles": [{"name", "layers", "description",
    ...}, ...]} — the OS-side generator's contract; unknown extra
    fields per entry are the generator's business and read through.

    Raises ManifestError when the resolved file is unreadable or not
    parseable (exit-2 path, like the manifests). ABSENCE is not an
    error here: when no file resolves (no env override and no fallback
    file, or an override naming an absent file), returns [] and the
    command layer turns that into the exit-1 message naming
    KAILASH_PROFILES.
    """
    path = profiles_path()
    if path is None:
        return []
    try:
        with open(path) as f:
            doc = json.load(f)
    except OSError:
        raise ManifestError("profiles file not readable: %s" % path)
    except ValueError as exc:
        raise ManifestError(
            "profiles file not parseable: %s: %s" % (path, exc))
    if not isinstance(doc, dict) or not isinstance(doc.get("profiles"), list):
        raise ManifestError(
            "profiles file malformed: %s carries no top-level 'profiles' list"
            % path)
    return doc["profiles"]


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
