# FYP Research — Kubernetes-Native DDoS Defense Framework

> **An Intelligent Kubernetes-Native DDoS Defense Framework Using eBPF-Based Network Observability, Graph-Based Anomaly Detection, and Adaptive Rate Limiting**

**Team:** [Team Members] · **Supervisor:** [Supervisor Name] · **Year:** 2025–2026

---

## Repository Structure

```
FYP Research/
├── .github/
│   ├── workflows/
│   │   └── daily_paper.yml          ← 📅 Daily paper reminder (9 AM IST)
│   └── paper-reminder/
│       ├── daily_paper.py           ← 🐍 Paper selection script
│       ├── papers.json              ← 📚 30 curated research papers
│       ├── state.json               ← 🔄 Auto-generated: tracks shown papers
│       └── README.md                ← 📖 Setup instructions
│
└── report/                          ← 📝 LaTeX report (upload to Overleaf)
    ├── main.tex                     ← Master LaTeX document
    ├── references.bib               ← 40+ BibTeX entries
    └── chapters/
        ├── ch01_introduction.tex    ← ✅ Full draft
        ├── ch02_background.tex      ← ✅ Full draft
        ├── ch03_literature_review.tex ← ✅ Full draft
        ├── ch04_design.tex          ← ✅ First-cut design
        ├── ch05_implementation.tex  ← 🔴 In progress
        ├── ch06_evaluation.tex      ← 🔴 Pending
        ├── ch07_discussion.tex      ← 🔴 Pending
        └── ch08_conclusion.tex      ← 🔴 Pending
```

---

## Daily Paper Reminder

Every morning at **9:00 AM IST**, a new research paper is automatically posted as a GitHub Issue.

➡️ See [`.github/paper-reminder/README.md`](.github/paper-reminder/README.md) for setup instructions.

**First-time setup:** Push this repo to GitHub, go to **Actions** tab, and click **"Run workflow"** to get your first paper immediately.

---

## Report (Overleaf)

Upload the `report/` folder to [Overleaf](https://overleaf.com):
1. Zip the `report/` directory
2. **New Project → Upload Project** on Overleaf
3. Set compiler: **pdfLaTeX**, bibliography tool: **Biber**

---

## Quick Links

- [📄 Issues (Daily Papers)](../../issues?label=📄+daily-paper) — your daily reading list
- [📚 Literature Survey](../../issues?label=📚+literature)
- [🔴 Must-Read Papers](../../issues?label=🔴+must-read)
- [📖 Overleaf Report](https://overleaf.com) — link to your project here

---

## Research Summary

| Item | Details |
|------|---------|
| **Topic** | Kubernetes-native DDoS detection & mitigation |
| **Key Technology** | eBPF (Cilium/Hubble) + Graph Neural Networks |
| **Detection Model** | Graph Autoencoder → GraphSAGE |
| **Mitigation** | XDP/TC adaptive rate limiting + CiliumNetworkPolicy |
| **Testbed** | Kind + Google Online Boutique |
| **Target Venue** | IEEE TNSM / ACM CoNEXT / Computers & Security |

---

*Undergraduate FYP · BSc (Hons) Computer Science & Engineering (Cybersecurity)*
