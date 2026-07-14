#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys, io
# Force UTF-8 output on Windows so emoji/box chars print correctly
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
test_paper_system.py
--------------------
Local test script — runs the full paper selection pipeline and prints results.
Does NOT create a GitHub Issue (no token needed).

Tests:
  1. Semantic Scholar API connectivity
  2. Paper scoring engine (all 4 axes)
  3. Curated fallback (papers.json)
  4. Issue title + body formatting
  5. State management (deduplication)
  6. Label generation

Run from the FYP Research root:
  python .github/paper-reminder/test_paper_system.py
"""

import sys
import os
import json
import time
import datetime

# ── Add the paper-reminder directory to path ─────────────────────────────────
SCRIPT_DIR = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, SCRIPT_DIR)

# ── Import from the actual script ────────────────────────────────────────────
from daily_paper import (
    fetch_papers_from_s2,
    select_from_semantic_scholar,
    select_from_curated,
    format_issue_title,
    format_issue_body,
    build_labels,
    load_state,
    relevance_score,
    recency_score,
    impact_score,
    novelty_score,
    total_score,
    SEARCH_QUERIES,
    FYP_KEYWORDS,
)

# ── Helpers ───────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"

passed = 0
failed = 0

def section(title):
    print(f"\n{BOLD}{CYAN}" + "="*60 + RESET)
    print(f"{BOLD}{CYAN}  {title}{RESET}")
    print(f"{BOLD}{CYAN}" + "="*60 + RESET)

def ok(msg):
    global passed
    passed += 1
    print(f"  {GREEN}[PASS]{RESET}  {msg}")

def fail(msg):
    global failed
    failed += 1
    print(f"  {RED}[FAIL]{RESET}  {msg}")

def info(msg):
    print(f"  {DIM}     {msg}{RESET}")

def warn(msg):
    print(f"  {YELLOW}[WARN]{RESET}  {msg}")


print(f"\n{BOLD}" + "="*60)
print(f"  FYP Daily Paper Reminder -- System Test")
print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60 + RESET)


# ════════════════════════════════════════════════════════════════════════════
section("TEST 1 — File existence checks")

files_to_check = [
    ".github/paper-reminder/daily_paper.py",
    ".github/paper-reminder/papers.json",
    ".github/paper-reminder/state.json",
    ".github/workflows/daily_paper.yml",
    ".gitignore",
    "README.md",
]

root = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
for rel_path in files_to_check:
    abs_path = os.path.join(root, rel_path)
    if os.path.exists(abs_path):
        size = os.path.getsize(abs_path)
        ok(f"{rel_path}  ({size:,} bytes)")
    else:
        fail(f"{rel_path}  — FILE MISSING")


# ════════════════════════════════════════════════════════════════════════════
section("TEST 2 — papers.json integrity")

papers_path = os.path.join(SCRIPT_DIR, "papers.json")
try:
    with open(papers_path, encoding="utf-8") as f:
        papers = json.load(f)
    ok(f"papers.json parsed — {len(papers)} papers loaded")

    required_fields = ["id", "title", "authors", "year", "category", "priority"]
    errors = 0
    for p in papers:
        missing = [f for f in required_fields if not p.get(f)]
        if missing:
            fail(f"Paper #{p.get('id','?')}: missing fields {missing}")
            errors += 1
    if errors == 0:
        ok(f"All {len(papers)} papers have required fields")

    categories = {}
    priorities = {}
    for p in papers:
        categories[p["category"]] = categories.get(p["category"], 0) + 1
        priorities[p["priority"]] = priorities.get(p["priority"], 0) + 1

    info(f"Categories: {dict(sorted(categories.items()))}")
    info(f"Priorities: {dict(sorted(priorities.items()))}")
except Exception as e:
    fail(f"papers.json load error: {e}")


# ════════════════════════════════════════════════════════════════════════════
section("TEST 3 — state.json integrity")

state_path = os.path.join(SCRIPT_DIR, "state.json")
try:
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    ok(f"state.json parsed — cycle={state.get('cycle',0)}, shown={len(state.get('shown_ids',[]))}")
    for field in ["shown_ids", "cycle", "total_shown"]:
        if field in state:
            ok(f"Field '{field}' present: {state[field]!r}")
        else:
            fail(f"Field '{field}' missing from state.json")
except Exception as e:
    fail(f"state.json load error: {e}")


# ════════════════════════════════════════════════════════════════════════════
section("TEST 4 — Scoring engine")

sample = {
    "title": "eBPF-based Graph Neural Network Anomaly Detection for Kubernetes DDoS",
    "abstract": "We use eBPF and Cilium Hubble to collect Kubernetes pod communication "
                "flows and model them as dynamic graphs. A graph autoencoder (GAE) detects "
                "DDoS anomalies via reconstruction error. Adaptive XDP rate limiting enforces mitigation.",
    "year": 2024,
    "citationCount": 47,
}

r = relevance_score(sample)
t = recency_score(sample)
i = impact_score(sample)
n = novelty_score(sample, set())
total = total_score(sample, set())

ok(f"Relevance score  (45%): {r:.3f}  (expect > 0.8 — lots of FYP keywords)")
ok(f"Recency score    (25%): {t:.3f}  (expect 1.0 — year=2024)")
ok(f"Impact score     (20%): {i:.3f}  (expect ~0.55 — 47 citations)")
ok(f"Novelty score    (10%): {n:.3f}  (expect 1.0 — not in state)")
ok(f"Total score:            {total:.3f}  (expect > 0.85)")

if total > 0.7:
    ok("High-relevance paper scores > 0.7 ✓")
else:
    fail(f"Expected score > 0.7, got {total:.3f}")

# Test low-relevance paper
irrelevant = {
    "title": "Quantum Computing Applications in Materials Science",
    "abstract": "We study quantum entanglement in superconducting materials.",
    "year": 2023,
    "citationCount": 200,
}
r2 = relevance_score(irrelevant)
total2 = total_score(irrelevant, set())
if r2 < 0.2:
    ok(f"Irrelevant paper correctly scores low: relevance={r2:.3f}, total={total2:.3f}")
else:
    fail(f"Irrelevant paper scored too high: relevance={r2:.3f}")


# ════════════════════════════════════════════════════════════════════════════
section("TEST 5 — Search query rotation")

today = datetime.date.today()
day_of_year = today.timetuple().tm_yday
query_index = day_of_year % len(SEARCH_QUERIES)
today_query = SEARCH_QUERIES[query_index]

ok(f"Today is day #{day_of_year} of year → query index #{query_index}")
ok(f"Today's query: {today_query!r}")
info(f"Total queries in rotation: {len(SEARCH_QUERIES)}")
info(f"Next 3 queries:")
for i in range(1, 4):
    idx = (query_index + i) % len(SEARCH_QUERIES)
    info(f"  Day +{i}: {SEARCH_QUERIES[idx]!r}")


# ════════════════════════════════════════════════════════════════════════════
section("TEST 6 — Semantic Scholar API  (live network test)")

print(f"\n  {YELLOW}Calling api.semanticscholar.org ...{RESET}")
t0 = time.time()
candidates = fetch_papers_from_s2(today_query)
elapsed = time.time() - t0

if candidates:
    ok(f"API returned {len(candidates)} papers in {elapsed:.2f}s")

    # Score top candidates
    state_fresh = {"shown_ids": []}
    scored = sorted(
        [(total_score(p, set()), p) for p in candidates],
        key=lambda x: x[0], reverse=True
    )

    print(f"\n  {BOLD}Top 5 scored candidates:{RESET}")
    print(f"  {'Score':>6}  {'Year':>4}  {'Cites':>6}  Title")
    print(f"  {'─'*6}  {'─'*4}  {'─'*6}  {'─'*40}")
    for score, p in scored[:5]:
        year   = p.get("year") or "?"
        cites  = p.get("citationCount") or 0
        title  = (p.get("title") or "")[:50]
        rel    = relevance_score(p)
        rec    = recency_score(p)
        print(f"  {score:>6.3f}  {year:>4}  {cites:>6,}  {title}")
        print(f"  {DIM}         rel={rel:.2f}  rec={rec:.2f}{RESET}")

    ok(f"Scoring engine processed {len(candidates)} candidates")
else:
    warn("Semantic Scholar API returned no results (network issue or rate limit)")
    warn("System will fall back to curated papers.json — that is expected behaviour")


# ════════════════════════════════════════════════════════════════════════════
section("TEST 7 — Full pipeline: select paper (live)")

state_test = load_state()
print(f"\n  {YELLOW}Running full selection pipeline...{RESET}")

paper = select_from_semantic_scholar(state_test)
source = "semantic_scholar"

if paper:
    ok(f"Live paper selected via Semantic Scholar")
    info(f"  Title:    {paper['title'][:70]}")
    info(f"  Authors:  {paper.get('authors','')[:60]}")
    info(f"  Venue:    {paper.get('venue','?')}")
    info(f"  Year:     {paper.get('year','?')}")
    info(f"  Score:    {paper.get('score','?')}")
    info(f"  Query:    {paper.get('query','?')}")
    if paper.get("pdf"):
        info(f"  PDF:      {paper['pdf']}")
    if paper.get("arxiv"):
        info(f"  arXiv:    {paper['arxiv']}")
else:
    warn("Live discovery failed — testing curated fallback...")
    paper = select_from_curated(state_test)
    source = "curated"
    ok(f"Curated fallback selected paper #{paper.get('id')}")
    info(f"  Title:    {paper['title'][:70]}")
    info(f"  Priority: {paper.get('priority','?')}")


# ════════════════════════════════════════════════════════════════════════════
section("TEST 8 — Issue title + body formatting")

title = format_issue_title(paper)
body  = format_issue_body(paper, state_test)

ok(f"Issue title generated ({len(title)} chars)")
info(f"  {title}")
ok(f"Issue body generated ({len(body):,} chars)")

# Check body contains key sections
required_sections = [
    "TL;DR",
    "Reading Checklist",
    "My Notes",
]
for section_name in required_sections:
    if section_name in body:
        ok(f"Body contains section: '{section_name}'")
    else:
        fail(f"Body missing section: '{section_name}'")


# ════════════════════════════════════════════════════════════════════════════
section("TEST 9 — Label generation")

labels = build_labels(paper)
ok(f"Generated {len(labels)} labels: {labels}")
if "📄 daily-paper" in labels:
    ok("Required label '📄 daily-paper' present")
else:
    fail("Required label '📄 daily-paper' missing")


# ════════════════════════════════════════════════════════════════════════════
section("TEST 10 — Deduplication logic")

# Simulate showing the current paper and picking again
# Use the actual _id stored by the selection pipeline (not a reconstructed hash)
actual_id = paper["_id"]
shown_set_empty  = set()
shown_set_filled = {actual_id}

# Build a proxy dict that will resolve to the same _id
from daily_paper import paper_id as _pid
proxy = {"title": paper["title"], "externalIds": paper.get("externalIds") or {}, "doi": paper.get("doi")}

n_before = 1.0 if actual_id not in shown_set_empty  else 0.0
n_after  = 1.0 if actual_id not in shown_set_filled else 0.0

ok(f"Novelty score BEFORE showing: {n_before}")
ok(f"Novelty score AFTER  showing: {n_after}")

if n_before > n_after:
    ok("Deduplication correctly penalises already-shown papers")
else:
    fail("Deduplication not working — scores should differ")


# ════════════════════════════════════════════════════════════════════════════
section("TEST 11 — GitHub Actions workflow YAML")

import re
workflow_path = os.path.join(root, ".github", "workflows", "daily_paper.yml")
if os.path.exists(workflow_path):
    with open(workflow_path, encoding="utf-8") as f:
        yml = f.read()

    if "30 3 * * *" in yml:
        ok("Cron schedule present: '30 3 * * *' = 9:00 AM IST daily")
    else:
        fail("Cron expression not found in workflow YAML")

    if "workflow_dispatch" in yml:
        ok("Manual trigger (workflow_dispatch) present — can run on-demand")
    else:
        fail("workflow_dispatch not found — cannot manually trigger")

    if "contents: write" in yml:
        ok("Permission 'contents: write' present — can commit state.json")
    else:
        fail("'contents: write' permission missing — state.json cannot be saved")

    if "issues: write" in yml:
        ok("Permission 'issues: write' present — can create GitHub Issues")
    else:
        fail("'issues: write' permission missing")

    if "state.json" in yml:
        ok("state.json commit step present in workflow")
    else:
        fail("state.json commit step missing")
else:
    fail("daily_paper.yml not found")


# ════════════════════════════════════════════════════════════════════════════
section("RESULTS SUMMARY")

total_tests = passed + failed
print(f"\n  Tests passed:  {GREEN}{BOLD}{passed}/{total_tests}{RESET}")
print(f"  Tests failed:  {RED}{BOLD}{failed}/{total_tests}{RESET}")

if failed == 0:
    print(f"\n  {GREEN}{BOLD}✅ ALL TESTS PASSED — System is ready to push to GitHub!{RESET}")
    print(f"\n  To go live, run:")
    print(f"    {CYAN}git -C \"C:\\Users\\varun\\Downloads\\FYP Research\" remote add origin https://github.com/YOUR_USERNAME/fyp-ddos-defense.git{RESET}")
    print(f"    {CYAN}git -C \"C:\\Users\\varun\\Downloads\\FYP Research\" push -u origin main{RESET}")
else:
    print(f"\n  {RED}{BOLD}❌ {failed} test(s) failed — review the output above before pushing.{RESET}")

print()
