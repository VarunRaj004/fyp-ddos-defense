#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test: verify ResearchGate URL generation for all 30 curated papers."""
import sys, io, os, json
sys.path.insert(0, os.path.dirname(__file__))
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from daily_paper import rg_url

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
with open(os.path.join(ROOT, ".github", "paper-reminder", "papers.json"), encoding="utf-8") as f:
    papers = json.load(f)

print("\n--- ResearchGate URL test for all 30 curated papers ---\n")
doi_count    = 0
search_count = 0

for p in papers:
    url  = rg_url(p)
    kind = "DOI   " if "/publication/" in url else "SEARCH"
    if kind == "DOI   ":
        doi_count += 1
    else:
        search_count += 1
    title = p["title"][:52]
    print(f"  [{kind}] #{p['id']:02d}  {title}")
    print(f"           {url[:85]}")

print()
print(f"  Direct DOI links : {doi_count}/30")
print(f"  Title search     : {search_count}/30")
print()

# Spot-check a few known DOI papers
tests = [
    # (paper_id, expected_fragment)
    (1,  "10.1145"),   # XDP — dl.acm.org/doi/10.1145/...
    (2,  "10.1109"),   # E-GraphSAGE — doi.org/10.1109/...
    (4,  "10.1109"),   # LUCID — doi.org/10.1109/...
]
print("  Spot checks:")
id_map = {p["id"]: p for p in papers}
all_ok = True
for pid, fragment in tests:
    p   = id_map[pid]
    url = rg_url(p)
    ok  = fragment in url
    status = "[OK]  " if ok else "[FAIL]"
    print(f"    {status} Paper #{pid}: {p['title'][:45]}")
    print(f"            {url[:80]}")
    if not ok:
        all_ok = False

print()
print("  Result:", "ALL PASS" if all_ok else "SOME FAILURES - check above")
print()
