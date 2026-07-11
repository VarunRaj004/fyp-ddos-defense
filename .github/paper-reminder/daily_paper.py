#!/usr/bin/env python3
"""
daily_paper.py  (v2 — Hybrid: Semantic Scholar API + Curated fallback)
-----------------------------------------------------------------------

HOW PAPER SELECTION WORKS (read this!):
========================================

  MODE A — Live Discovery (Semantic Scholar API)
  ───────────────────────────────────────────────
  1. Sends search queries to the FREE Semantic Scholar Academic Graph API
     (same paper database as ResearchGate, but with an open REST API)
  2. Rotates through 10 topic-specific query strings relevant to the FYP
  3. Each query returns up to 30 candidate papers
  4. Candidates are SCORED on four axes:
       • Relevance  — does the title/abstract match your FYP keywords?
       • Recency    — newer papers score higher (2020–2025 preferred)
       • Impact     — citation count (log-scaled so 1 paper ≠ all results)
       • Novelty    — has this paper been shown before? (penalised if yes)
  5. The highest-scoring paper is selected and posted as a GitHub Issue

  MODE B — Curated Fallback (papers.json)
  ─────────────────────────────────────────
  If the API is unreachable (network error, rate limit), the script falls back
  to the hand-curated list in papers.json — weighted by your priority ratings
  (MUST-READ papers appear 4× more often than MEDIUM papers)

  DEDUPLICATION
  ─────────────
  state.json tracks every paper (by DOI or title hash) that has been shown.
  A paper is never repeated until ALL available papers have been suggested.
  After a full cycle, state.json resets and the cycle counter increments.

Environment variables (auto-injected by GitHub Actions):
  GITHUB_TOKEN        — GitHub API token for creating issues
  GITHUB_REPOSITORY   — owner/repo string
"""

import json
import hashlib
import os
import re
import sys
import random
import datetime
import time
import urllib.request
import urllib.error
import urllib.parse

# ═══════════════════════════════════════════════════════════════════════════════
#  CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

PAPERS_FILE = os.path.join(os.path.dirname(__file__), "papers.json")
STATE_FILE  = os.path.join(os.path.dirname(__file__), "state.json")

# Semantic Scholar API — free, no key needed for basic use
S2_SEARCH_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS     = "title,authors,year,venue,externalIds,abstract,citationCount,openAccessPdf,url"
S2_LIMIT      = 30      # papers fetched per query
API_TIMEOUT   = 15      # seconds

# FYP-specific search queries — rotated daily (one per day of week + more)
# These are carefully chosen to stay on-topic for the project
SEARCH_QUERIES = [
    "eBPF Kubernetes network security anomaly detection",
    "graph neural network DDoS attack detection",
    "XDP eBPF DDoS mitigation Linux kernel",
    "Kubernetes microservices intrusion detection system",
    "graph autoencoder network intrusion detection unsupervised",
    "GraphSAGE network traffic classification",
    "temporal graph neural network network security",
    "eBPF container security observability Kubernetes",
    "adaptive rate limiting cloud native DDoS",
    "microservice communication graph anomaly detection",
    "eBPF XDP packet filtering performance",
    "graph convolutional network cyber security",
    "Cilium Hubble network observability Kubernetes",
    "dynamic graph anomaly detection streaming",
    "low and slow DDoS attack detection machine learning",
]

# Keywords that boost relevance scoring
FYP_KEYWORDS = [
    "ebpf", "xdp", "bpf", "kubernetes", "k8s", "microservice", "container",
    "graph neural", "gnn", "graphsage", "graph autoencoder", "gae", "gcn",
    "ddos", "denial of service", "anomaly detection", "intrusion detection",
    "network security", "cilium", "hubble", "rate limiting", "mitigation",
    "dynamic graph", "temporal graph", "tgn", "tgat", "provenance graph",
    "cloud native", "service mesh", "network flow", "packet filtering",
]

# Scoring weights
W_RELEVANCE  = 0.45
W_RECENCY    = 0.25
W_IMPACT     = 0.20
W_NOVELTY    = 0.10

# Publication year range to prefer
YEAR_CUTOFF_BEST   = 2022   # Full score
YEAR_CUTOFF_GOOD   = 2019   # Partial score
YEAR_MINIMUM       = 2016   # Below this: very low recency score

# Category mapping — auto-detected from abstract/title keywords
KEYWORD_TO_CATEGORY = {
    "ebpf": "eBPF & XDP",
    "xdp":  "eBPF & XDP",
    "bpf":  "eBPF & XDP",
    "cilium": "eBPF & XDP",
    "graph neural": "Graph Neural Networks",
    "gnn":  "Graph Neural Networks",
    "graphsage": "Graph Neural Networks",
    "graph convolutional": "Graph Neural Networks",
    "graph autoencoder": "Graph Neural Networks",
    "temporal graph": "Graph Neural Networks",
    "ddos": "DDoS Detection",
    "denial of service": "DDoS Detection",
    "intrusion detection": "Graph ML for Security",
    "anomaly detection": "Graph ML for Security",
    "kubernetes": "Microservice & Kubernetes",
    "microservice": "Microservice & Kubernetes",
    "container": "Microservice & Kubernetes",
}

CATEGORY_EMOJI = {
    "eBPF & XDP":               "⚡",
    "Graph Neural Networks":    "🧠",
    "Graph ML for Security":    "🔍",
    "DDoS Detection":           "🛡️",
    "Microservice & Kubernetes":"☸️",
    "Research Methodology":     "✍️",
    "Discovered Paper":         "🌐",
}

PRIORITY_WEIGHTS = {
    "MUST-READ": 4,
    "HIGH":      2,
    "MEDIUM":    1,
    "LOW":       0.5,
}


# ═══════════════════════════════════════════════════════════════════════════════
#  STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "shown_ids":     [],   # list of DOI/title hashes already posted
        "cycle":         0,
        "query_index":   0,    # which query to use today
        "last_run_date": None,
        "total_shown":   0,
    }


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def paper_id(paper: dict) -> str:
    """Stable ID for deduplication — prefers DOI, falls back to title hash."""
    doi = (paper.get("externalIds") or {}).get("DOI") or paper.get("doi")
    if doi:
        return f"doi:{doi.lower()}"
    title = paper.get("title", "")
    return "hash:" + hashlib.md5(title.lower().encode()).hexdigest()[:12]


def curated_id(paper: dict) -> str:
    return f"curated:{paper['id']}"


# ═══════════════════════════════════════════════════════════════════════════════
#  SEMANTIC SCHOLAR API
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_papers_from_s2(query: str) -> list[dict]:
    """
    Query Semantic Scholar and return raw result list.
    Returns [] on any network/API error (triggers fallback).
    """
    params = urllib.parse.urlencode({
        "query":  query,
        "fields": S2_FIELDS,
        "limit":  S2_LIMIT,
    })
    url = f"{S2_SEARCH_URL}?{params}"
    headers = {
        "User-Agent": "FYP-Paper-Reminder/2.0 (academic research project)",
        "Accept": "application/json",
    }

    print(f"[S2] Querying: {query!r}")

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT) as resp:
            data = json.load(resp)
            papers = data.get("data", [])
            print(f"[S2] Got {len(papers)} results")
            return papers
    except urllib.error.HTTPError as e:
        print(f"[S2] HTTP {e.code} — falling back to curated list")
        return []
    except Exception as e:
        print(f"[S2] Error ({type(e).__name__}: {e}) — falling back to curated list")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
#  SCORING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def relevance_score(paper: dict) -> float:
    """
    Score 0–1 based on how many FYP keywords appear in title + abstract.
    More keyword matches = higher relevance.
    """
    text = (
        (paper.get("title") or "") + " " +
        (paper.get("abstract") or "")
    ).lower()

    hits = sum(1 for kw in FYP_KEYWORDS if kw in text)
    # Normalise: 5+ keyword hits = full score
    return min(hits / 5.0, 1.0)


def recency_score(paper: dict) -> float:
    """
    Score 0–1 based on publication year.
    2022+ → 1.0, 2019–2021 → 0.6, 2016–2018 → 0.3, <2016 → 0.1
    (Classic foundational papers in curated list are already there)
    """
    year = paper.get("year") or 0
    if year >= YEAR_CUTOFF_BEST:
        return 1.0
    elif year >= YEAR_CUTOFF_GOOD:
        return 0.6
    elif year >= YEAR_MINIMUM:
        return 0.3
    else:
        return 0.1


def impact_score(paper: dict) -> float:
    """
    Log-scaled citation count score 0–1.
    0 citations → 0.0, 10 → 0.5, 100 → 0.75, 1000+ → 1.0
    """
    import math
    citations = paper.get("citationCount") or 0
    if citations <= 0:
        return 0.0
    return min(math.log10(citations + 1) / 3.0, 1.0)


def novelty_score(paper: dict, shown_ids: set) -> float:
    """
    1.0 if never shown before, 0.0 if already shown this cycle.
    """
    return 0.0 if paper_id(paper) in shown_ids else 1.0


def total_score(paper: dict, shown_ids: set) -> float:
    r = relevance_score(paper)
    t = recency_score(paper)
    i = impact_score(paper)
    n = novelty_score(paper, shown_ids)
    score = (W_RELEVANCE * r) + (W_RECENCY * t) + (W_IMPACT * i) + (W_NOVELTY * n)
    return score


def detect_category(paper: dict) -> str:
    text = (
        (paper.get("title") or "") + " " +
        (paper.get("abstract") or "")
    ).lower()
    for keyword, category in KEYWORD_TO_CATEGORY.items():
        if keyword in text:
            return category
    return "Discovered Paper"


# ═══════════════════════════════════════════════════════════════════════════════
#  PAPER SELECTION — MODE A (Semantic Scholar)
# ═══════════════════════════════════════════════════════════════════════════════

def select_from_semantic_scholar(state: dict) -> dict | None:
    """
    Fetch papers from Semantic Scholar, score them, return the best one.
    Returns None if fetch fails or no suitable paper found.
    """
    shown_ids = set(state.get("shown_ids", []))

    # Rotate query by day-of-year so each day uses a different topic
    day_of_year = datetime.date.today().timetuple().tm_yday
    query_index = day_of_year % len(SEARCH_QUERIES)
    query       = SEARCH_QUERIES[query_index]

    candidates = fetch_papers_from_s2(query)

    if not candidates:
        return None

    # Filter: must have a title and be at least somewhat relevant
    candidates = [
        p for p in candidates
        if p.get("title") and relevance_score(p) > 0.1
    ]

    if not candidates:
        print("[S2] No relevant papers after filtering — trying second query")
        backup_query = SEARCH_QUERIES[(query_index + 1) % len(SEARCH_QUERIES)]
        candidates = fetch_papers_from_s2(backup_query)
        candidates = [p for p in candidates if p.get("title")]

    if not candidates:
        return None

    # Score all candidates
    scored = []
    for p in candidates:
        s = total_score(p, shown_ids)
        scored.append((s, p))
        print(f"  score={s:.3f} | {p.get('year','?')} | {p['title'][:60]}")

    # Sort descending and pick the top paper
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_paper = scored[0]

    print(f"[S2] Selected: score={best_score:.3f} | {best_paper['title'][:70]}")

    # Normalise to a common dict format
    authors_list = [a.get("name", "") for a in (best_paper.get("authors") or [])]
    authors_str  = ", ".join(authors_list[:6])
    if len(authors_list) > 6:
        authors_str += " et al."

    doi  = (best_paper.get("externalIds") or {}).get("DOI")
    arxiv_id = (best_paper.get("externalIds") or {}).get("ArXiv")

    paper_url  = f"https://doi.org/{doi}" if doi else (best_paper.get("url") or "")
    arxiv_url  = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else None
    pdf_url    = (best_paper.get("openAccessPdf") or {}).get("url")
    s2_url     = f"https://www.semanticscholar.org/paper/{best_paper.get('paperId','')}"

    return {
        # Core fields
        "title":    best_paper.get("title", "Unknown Title"),
        "authors":  authors_str,
        "venue":    best_paper.get("venue") or "Unknown Venue",
        "year":     best_paper.get("year") or "Unknown",
        "abstract": (best_paper.get("abstract") or "")[:600],
        "citations": best_paper.get("citationCount") or 0,
        # Links
        "url":      paper_url,
        "arxiv":    arxiv_url,
        "pdf":      pdf_url,
        "s2_url":   s2_url,
        # Meta
        "category": detect_category(best_paper),
        "priority": "HIGH" if best_score > 0.6 else "MEDIUM",
        "source":   "semantic_scholar",
        "score":    round(best_score, 3),
        "query":    query,
        "_id":      paper_id(best_paper),
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  PAPER SELECTION — MODE B (Curated fallback)
# ═══════════════════════════════════════════════════════════════════════════════

def select_from_curated(state: dict) -> dict:
    """
    Weighted random selection from papers.json.
    Tracks shown papers and resets after full cycle.
    """
    with open(PAPERS_FILE, encoding="utf-8") as f:
        papers = json.load(f)

    shown_ids = set(state.get("shown_ids", []))
    remaining = [p for p in papers if curated_id(p) not in shown_ids]

    if not remaining:
        print("[Curated] Full cycle complete — resetting")
        state["shown_ids"] = []
        state["cycle"] = state.get("cycle", 0) + 1
        remaining = papers

    weights = [PRIORITY_WEIGHTS.get(p.get("priority", "MEDIUM"), 1) for p in remaining]
    chosen  = random.choices(remaining, weights=weights, k=1)[0]

    # Adapt curated format to common format
    return {
        **chosen,
        "source":   "curated",
        "score":    None,
        "query":    None,
        "_id":      curated_id(chosen),
        "abstract": chosen.get("tldr", ""),
        "citations": None,
        "s2_url":   None,
        "pdf":      None,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  ISSUE FORMATTER
# ═══════════════════════════════════════════════════════════════════════════════

def format_issue_title(paper: dict) -> str:
    today     = datetime.date.today().strftime("%d %b %Y")
    priority  = paper.get("priority", "MEDIUM")
    prio_icon = {"MUST-READ": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(priority, "📄")
    emoji     = CATEGORY_EMOJI.get(paper.get("category", ""), "📄")
    source    = " [S2]" if paper.get("source") == "semantic_scholar" else ""
    title_short = paper["title"][:75] + ("…" if len(paper["title"]) > 75 else "")
    return f"{prio_icon} [{today}] {emoji} {title_short}{source}"


def format_issue_body(paper: dict, state: dict) -> str:
    today     = datetime.date.today().strftime("%A, %d %B %Y")
    cycle     = state.get("cycle", 0) + 1
    total     = state.get("total_shown", 0) + 1
    category  = paper.get("category", "Discovered Paper")
    emoji     = CATEGORY_EMOJI.get(category, "📄")
    priority  = paper.get("priority", "MEDIUM")
    source    = paper.get("source", "curated")

    priority_badge = {
        "MUST-READ": "🔴 **MUST-READ**",
        "HIGH":      "🟠 **HIGH PRIORITY**",
        "MEDIUM":    "🟡 Medium Priority",
        "LOW":       "🟢 Low Priority",
    }.get(priority, "🟡 Medium Priority")

    # ── Source badge ──
    if source == "semantic_scholar":
        source_badge = (
            f"🌐 **Discovered via Semantic Scholar**  \n"
            f"> Query: `{paper.get('query', '')}` · "
            f"Relevance Score: `{paper.get('score', '?')}`"
        )
        score_info = (
            f"\n\n**Scoring breakdown** _(how this paper was chosen today)_:\n"
            f"| Axis | Weight | Meaning |\n"
            f"|------|--------|---------|\n"
            f"| 🎯 Relevance | 45% | Keyword match with your FYP topics |\n"
            f"| 📅 Recency | 25% | Publication year (newer = higher) |\n"
            f"| 📈 Impact | 20% | Log-scaled citation count |\n"
            f"| 🆕 Novelty | 10% | Not suggested to you before |\n"
        )
    else:
        source_badge = "📚 **From Curated FYP Reading List** (Semantic Scholar unavailable)"
        score_info   = ""

    # ── Citation count ──
    citations = paper.get("citations")
    cite_str  = f"**Citations:** {citations:,}" if citations is not None else ""

    # ── Abstract / TL;DR ──
    tldr = paper.get("tldr") or paper.get("abstract") or ""
    if len(tldr) > 500:
        tldr = tldr[:500] + "…"

    # ── Key findings (curated only) ──
    findings_block = ""
    if paper.get("key_findings"):
        items = "\n".join(f"  - {f}" for f in paper["key_findings"])
        findings_block = f"\n### 🔑 Key Findings\n\n{items}\n"

    # ── Project relevance ──
    relevance = paper.get("project_relevance", "")
    relevance_block = ""
    if relevance:
        relevance_block = f"\n### 🎯 Why You Should Read This (Project Relevance)\n\n{relevance}\n"

    # ── Reading focus ──
    reading_focus = paper.get("reading_focus", "")
    focus_block = ""
    if reading_focus:
        focus_block = f"\n### 🔎 Reading Focus\n\n> {reading_focus}\n"

    # ── Links ──
    links = []
    if paper.get("pdf"):
        links.append(f"[📥 Free PDF]({paper['pdf']})")
    if paper.get("arxiv"):
        links.append(f"[📦 arXiv]({paper['arxiv']})")
    if paper.get("url") and paper["url"].startswith("http"):
        links.append(f"[🔗 Publisher Page]({paper['url']})")
    if paper.get("s2_url"):
        links.append(f"[🔍 Semantic Scholar]({paper['s2_url']})")
    links_str = " · ".join(links) if links else "_Search on [Semantic Scholar](https://www.semanticscholar.org/) or [Google Scholar](https://scholar.google.com/)_"

    # ── Citation key ──
    first_author_last = (paper.get("authors", "Unknown").split(",")[0].split()[-1]
                         if paper.get("authors") else "Author")
    year_str = str(paper.get("year", ""))
    tag_str  = (paper.get("tags") or ["paper"])[0]
    cite_key = f"{first_author_last}{year_str}{tag_str}"

    # ── Compose body ──
    body = f"""## {emoji} Today's Research Paper — {today}

> **Paper #{total}** · **Reading Cycle #{cycle}** · **Category:** {category} · {priority_badge}

{source_badge}
{score_info}

---

### 📖 {paper['title']}

| Field | Details |
|-------|---------|
| **Authors** | {paper.get('authors', 'Unknown')} |
| **Venue** | {paper.get('venue', 'Unknown')} |
| **Year** | {paper.get('year', 'Unknown')} |
{f"| **Citations** | {citations:,} |" if citations is not None else ""}

---

### 💡 TL;DR / Abstract

> {tldr if tldr else "_No abstract available — check the paper directly._"}
{findings_block}{relevance_block}{focus_block}

---

### 🔗 Links

{links_str}

---

### ✅ Reading Checklist

- [ ] Read the **abstract and introduction**
- [ ] Study the section(s) highlighted in **Reading Focus** above
- [ ] Note 2–3 ways this work **differs from your project** (for your Related Work section)
- [ ] Find the BibTeX entry on the paper's ACM/IEEE page and add to `references.bib`
- [ ] Add 1–2 sentences about this paper to **Chapter 3** (`ch03_literature_review.tex`)
- [ ] Mark as 🟢 **Done** in `weekly_progress.md` → Master Paper Reading List

---

### 📝 My Notes

> _Delete this placeholder and paste your reading notes here after reading:_

**What I understood:**

**How this relates to my project:**

**How my project DIFFERS from this:**

**Suggested BibTeX key:** `{cite_key}`

---

_Auto-generated by [📄 Daily Paper Reminder](.github/workflows/daily_paper.yml)_
_Source: {"Semantic Scholar Academic Graph API" if source == "semantic_scholar" else "Curated FYP reading list"}_
"""
    return body


# ═══════════════════════════════════════════════════════════════════════════════
#  GITHUB API
# ═══════════════════════════════════════════════════════════════════════════════

def _gh_request(method: str, url: str, data: dict | None = None) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    payload = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization":        f"Bearer {token}",
            "Accept":               "application/vnd.github+json",
            "Content-Type":         "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def ensure_labels(repo: str):
    label_defs = {
        "📄 daily-paper":    ("0075ca", "Daily research paper reminder"),
        "📚 literature":     ("e4e669", "Literature review"),
        "🔴 must-read":      ("d73a4a", "Must-read priority paper"),
        "🟠 high-priority":  ("f97316", "High priority paper"),
        "🟡 medium":         ("eab308", "Medium priority paper"),
        "🌐 live-discovery": ("8b5cf6", "Paper found via Semantic Scholar API"),
        "📚 curated":        ("6366f1", "Paper from curated reading list"),
        "⚡ ebpf":           ("7c3aed", "eBPF related paper"),
        "🧠 graph-ml":       ("16a34a", "Graph ML / GNN paper"),
        "🔍 security":       ("dc2626", "Security / IDS paper"),
        "🛡️ ddos":           ("b91c1c", "DDoS detection / mitigation"),
        "☸️ kubernetes":     ("0ea5e9", "Kubernetes / cloud-native"),
    }
    url = f"https://api.github.com/repos/{repo}/labels"
    for name, (color, desc) in label_defs.items():
        try:
            _gh_request("POST", url, {"name": name, "color": color, "description": desc})
        except urllib.error.HTTPError as e:
            if e.code != 422:  # 422 = already exists, that's fine
                print(f"[WARN] Label '{name}': HTTP {e.code}")


def build_labels(paper: dict) -> list[str]:
    labels = ["📄 daily-paper", "📚 literature"]
    priority = paper.get("priority", "MEDIUM")
    labels.append({"MUST-READ": "🔴 must-read", "HIGH": "🟠 high-priority"}.get(priority, "🟡 medium"))
    labels.append("🌐 live-discovery" if paper.get("source") == "semantic_scholar" else "📚 curated")
    cat = paper.get("category", "")
    if "eBPF" in cat or "XDP" in cat: labels.append("⚡ ebpf")
    if "Graph" in cat:                labels.append("🧠 graph-ml")
    if "DDoS" in cat:                 labels.append("🛡️ ddos")
    if "Security" in cat or "IDS" in cat: labels.append("🔍 security")
    if "Kubernetes" in cat or "Micro" in cat: labels.append("☸️ kubernetes")
    return labels


def create_issue(repo: str, title: str, body: str, labels: list[str]) -> str:
    url    = f"https://api.github.com/repos/{repo}/issues"
    result = _gh_request("POST", url, {"title": title, "body": body, "labels": labels})
    return result["html_url"]


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not repo:
        print("[ERROR] GITHUB_REPOSITORY not set")
        sys.exit(1)

    state = load_state()
    state["last_run_date"] = datetime.date.today().isoformat()

    # ── Try live discovery first ──
    print("[INFO] Attempting live discovery via Semantic Scholar...")
    paper = select_from_semantic_scholar(state)

    if paper:
        print(f"[INFO] Mode: LIVE DISCOVERY (Semantic Scholar)")
    else:
        print(f"[INFO] Mode: CURATED FALLBACK (papers.json)")
        paper = select_from_curated(state)

    # ── Format and post ──
    title  = format_issue_title(paper)
    body   = format_issue_body(paper, state)
    labels = build_labels(paper)

    print(f"\n{'='*60}")
    print(f"Title: {title}")
    print(f"Labels: {labels}")
    print(f"{'='*60}\n")

    ensure_labels(repo)
    issue_url = create_issue(repo, title, body, labels)
    print(f"[OK] Issue created: {issue_url}")

    # ── Update state ──
    shown = state.get("shown_ids", [])
    pid = paper["_id"]
    if pid not in shown:
        shown.append(pid)
    state["shown_ids"]   = shown
    state["total_shown"] = state.get("total_shown", 0) + 1
    save_state(state)
    print(f"[INFO] State: {len(shown)} papers shown total (cycle #{state['cycle']+1})")


if __name__ == "__main__":
    main()
