# 📄 Daily Research Paper Reminder

A GitHub Actions automation that posts **one curated research paper every day at 9 AM IST** as a GitHub Issue — complete with TL;DR, key findings, project relevance, and a reading checklist.

---

## How It Works

```
Every day at 9:00 AM IST (3:30 AM UTC)
         │
         ▼
GitHub Actions runs daily_paper.py
         │
         ▼
Picks a paper from papers.json
(weighted by priority: MUST-READ > HIGH > MEDIUM > LOW)
         │
         ▼
Creates a GitHub Issue with:
  📖 Full paper details
  💡 TL;DR summary
  🔑 Key findings
  🎯 Project relevance (specific to YOUR FYP)
  🔎 Reading focus (exactly what to pay attention to)
  ✅ Reading checklist
  📝 Notes template
         │
         ▼
Commits state.json to track shown papers
(cycles through all 30 papers before repeating)
```

---

## Paper Categories Covered

| Category | Papers | Priority |
|----------|--------|----------|
| ⚡ eBPF & XDP | 7 papers | XDP, Cilium, FlowSentryX, BPF-LSM... |
| 🧠 Graph Neural Networks | 7 papers | GAE, GraphSAGE, GCN, TGN, TGAT... |
| 🔍 Graph ML for Security | 5 papers | E-GraphSAGE, Kairos, Euler... |
| 🛡️ DDoS Detection | 5 papers | LUCID, Kitsune, Slowloris, Surveys... |
| ☸️ Microservice & Kubernetes | 4 papers | Cilium, MicroRank, CNCF Whitepaper... |
| ✍️ Research Methodology | 1 paper | How to write a good systems paper |

---

## Setup Instructions

### Step 1: Create a GitHub Repository

Push your FYP research folder to GitHub:

```powershell
cd "C:\Users\varun\Downloads\FYP Research"
git init
git add .
git commit -m "feat: initial FYP research repo with daily paper reminder"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### Step 2: Enable GitHub Actions

1. Go to your repository on GitHub
2. Click **Actions** tab
3. If prompted, click **"I understand my workflows, go ahead and enable them"**

### Step 3: Set Up Issue Labels (Automatic)

The script automatically creates all required labels on first run:
- `📄 daily-paper`, `📚 literature`
- `🔴 must-read`, `🟠 high-priority`, `🟡 medium`
- `⚡ ebpf`, `🧠 graph-ml`, `🛡️ ddos`, `☸️ kubernetes`

### Step 4: Enable GitHub Notifications

1. Go to **Settings → Notifications** in GitHub
2. Enable **Issues** notifications for this repository
3. You'll get an email every morning when the issue is created

### Step 5: Test It Now (Optional)

Trigger manually without waiting for tomorrow:
1. Go to **Actions** tab → **📄 Daily Research Paper Reminder**
2. Click **"Run workflow"** → **Run workflow**
3. Check the **Issues** tab in 30 seconds for your first paper!

---

## File Structure

```
.github/
├── workflows/
│   └── daily_paper.yml      ← GitHub Actions schedule definition
└── paper-reminder/
    ├── daily_paper.py       ← Main script: selects paper + creates issue
    ├── papers.json          ← 30 curated papers with full metadata
    ├── state.json           ← Auto-generated: tracks which papers shown
    └── README.md            ← This file
```

---

## Customising

### Adding New Papers

Add an entry to `papers.json` with this schema:

```json
{
  "id": 31,
  "title": "Paper Title",
  "authors": "Author 1, Author 2",
  "venue": "Conference/Journal Year",
  "year": 2024,
  "url": "https://doi.org/...",
  "arxiv": "https://arxiv.org/abs/...",
  "category": "Graph Neural Networks",
  "priority": "HIGH",
  "tags": ["tag1", "tag2"],
  "tldr": "One sentence summary.",
  "key_findings": [
    "Finding 1",
    "Finding 2"
  ],
  "project_relevance": "Why this matters for your FYP.",
  "reading_focus": "What specific sections to focus on."
}
```

**Priority values:** `MUST-READ` | `HIGH` | `MEDIUM` | `LOW`

**Category values:** `eBPF & XDP` | `Graph Neural Networks` | `Graph ML for Security` | `DDoS Detection` | `Microservice & Kubernetes` | `Research Methodology`

### Changing the Schedule

Edit the cron expression in `daily_paper.yml`:

```yaml
schedule:
  - cron: "30 3 * * *"   # 09:00 IST = 03:30 UTC
```

[Cron expression editor](https://crontab.guru/) — convert to UTC from your timezone.

### Skipping Weekends

```yaml
schedule:
  - cron: "30 3 * * 1-5"   # Monday to Friday only
```

---

## What a Daily Issue Looks Like

```
Title: 🔴 [10 Jul 2026] ⚡ The eXpress Data Path: Fast Programmable Packet...

Body:
## ⚡ Today's Research Paper — Thursday, 10 July 2026

> Reading Cycle: #1 · Category: eBPF & XDP · 🔴 MUST-READ

### 📖 The eXpress Data Path: Fast Programmable Packet Processing...

| Field    | Details                                          |
|----------|--------------------------------------------------|
| Authors  | Toke Høiland-Jørgensen, Daniel Borkmann et al.  |
| Venue    | ACM CoNEXT 2018                                  |
| Year     | 2018                                             |
| Tags     | `eBPF` `XDP` `DDoS` `packet-processing`          |

### 💡 TL;DR
> Introduces XDP — the earliest hook in the Linux kernel...

### 🔑 Key Findings
  - XDP achieves full line-rate packet drops on commodity NICs
  - ...

### 🎯 Why You Should Read This
  This is the foundation of your DDoS mitigation data plane...

### ✅ Reading Checklist
- [ ] Read abstract and introduction
- [ ] Study sections highlighted above
- [ ] Add to references.bib
- [ ] Update literature review
```

---

*Generated for FYP: Kubernetes-Native DDoS Defense Framework*
*Papers curated from: IEEE S&P, ACM CCS, USENIX, NDSS, NeurIPS, ICLR, CoNEXT (2013–2025)*
