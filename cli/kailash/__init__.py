"""kailash - the manifest-aware CLI over the two manifest files.

KA-14.1 (plan §7.1-7.4): the packaging surface is the wheel defined by
../pyproject.toml; loader + command core live here in kailash/. The CLI
generates from manifest/tools.yaml and manifest/categories.yaml - the
taxonomy's single home - and is never a second source of truth.
"""
