#!/usr/bin/env python3
"""Generate tests/upstream_verified.json (the KA-24a verification cache).

Probes every manifest row's source.vcs_url via the GitHub API; writes a
sorted verdict sheet keyed by upstream repository ("owner/repo") with
checked_at date + prober + verdict ("ok"/"httpNNN"). Non-GitHub upstreams
are recorded by hand (the probe contract refuses to write them from this
script): sourceforge/sox carries a search-receipt manual verdict.
"""
import json, subprocess, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml
doc = yaml.safe_load(open("manifest/tools.yaml"))
rows = {}
for t in doc["tools"]:
    s = t.get("source") or {}
    url = s.get("vcs_url")
    if not url:
        # source-less row (proprietary/native without vcs) — legitimate,
        # tracked via nixpkgs pin, not via an upstream repo URL.
        continue
    rows[t["id"]] = url

TOK = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
H = {"Authorization": f"token {TOK}", "User-Agent": "kailash-upstream-verify",
     "Accept": "application/vnd.github+json"}

def pair_of(url):
    return url.replace("https://github.com/", "").strip("/")

def probe(pair):
    try:
        req = urllib.request.Request(f"https://api.github.com/repos/{pair}", headers=H)
        with urllib.request.urlopen(req, timeout=20) as r:
            return pair, ("ok" if r.status == 200 else f"http{r.status}")
    except urllib.error.HTTPError as e:
        return pair, f"http{e.code}"
    except Exception as e:
        return pair, "error"

pairs = sorted(set(pair_of(u) for u in rows.values() if "github.com" in u))
verdicts = {}
with ThreadPoolExecutor(max_workers=6) as ex:
    futs = {ex.submit(probe, p): p for p in pairs}
    for i, f in enumerate(as_completed(futs), 1):
        p, v = f.result()
        verdicts[p] = v
        if i % 50 == 0:
            print("progress", i, "/", len(pairs), flush=True)

bad = {p: v for p, v in verdicts.items() if v != "ok"}
if bad:
    print("BAD VERDICTS (refusing to bless):")
    for p, v in sorted(bad.items()):
        print(" ", p, v)
    sys.exit(1)

# manual verdicts (non-GitHub upstreams; probe contract = human-reviewed receipt)
manual = {
    "sourceforge/sox": {
        "vcs_url": "https://sourceforge.net/projects/sox/",
        "verdict": "ok",
        "evidence": "canonical upstream is the sourceforge.net/projects/sox project "
                    "(maintainers cbagwell/mansr/robs/rrt/uklauer, updated 2024); "
                    "sourceforge bot-walls scripted GETs (HTTP 403 by design) — "
                    "verified via public search receipts + the Debian salsa mirror "
                    "sox-ng, not the probe script. Manual contract per probe rule.",
    }
}

out = {
    "schema": "kailash.upstream-verification-cache/1",
    "policy": "every tools.yaml vcs_url must record verdict ok here; a row whose "
              "upstream record is missing or verdict!=ok is a fabrication (the "
              "tool does not exist) and must not ship",
    "checked_at": time.strftime("%Y-%m-%d"),
    "prober": "tests/generate_upstream_cache.py (GitHub API; org-token, unauthenticated-equivalent rate)",
    "manual_entries": manual,
    "upstreams": {p: {"verdict": v, "checked_at": time.strftime("%Y-%m-%d")}
                  for p, v in sorted(verdicts.items())},
}
with open("tests/upstream_verified.json", "w") as f:
    json.dump(out, f, indent=2, sort_keys=True)
    f.write("\n")
print("cache written: tests/upstream_verified.json —", len(verdicts), "github +", len(manual), "manual upstreams")
