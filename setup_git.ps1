#!/usr/bin/env pwsh
<#
.SYNOPSIS
    One-command setup: initialises the FYP git repo and pushes to GitHub.

.DESCRIPTION
    Run this script ONCE from inside your "FYP Research" folder.
    It will:
      1. Verify git is installed
      2. Configure git user name/email if not already set
      3. Initialise the repo (git init)
      4. Stage and commit everything
      5. Ask you for your GitHub repo URL
      6. Push to GitHub
      7. Print the Actions URL so you can trigger the first paper immediately

.EXAMPLE
    cd "C:\Users\varun\Downloads\FYP Research"
    .\setup_git.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Colours ──────────────────────────────────────────────────────────────────
function Write-Step  ($msg) { Write-Host "`n  ▶  $msg" -ForegroundColor Cyan }
function Write-OK    ($msg) { Write-Host "  ✅  $msg" -ForegroundColor Green }
function Write-Warn  ($msg) { Write-Host "  ⚠️   $msg" -ForegroundColor Yellow }
function Write-Err   ($msg) { Write-Host "  ❌  $msg" -ForegroundColor Red }
function Write-Info  ($msg) { Write-Host "     $msg" -ForegroundColor Gray }

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "  ║   FYP Research — Git Setup & GitHub Push            ║" -ForegroundColor Magenta
Write-Host "  ║   Daily Paper Reminder Automation                   ║" -ForegroundColor Magenta
Write-Host "  ╚══════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

# ── Step 1: Check git is installed ───────────────────────────────────────────
Write-Step "Checking git installation..."
try {
    $gitVersion = git --version 2>&1
    Write-OK "Found: $gitVersion"
} catch {
    Write-Err "git is not installed. Download from https://git-scm.com/download/win"
    exit 1
}

# ── Step 2: Make sure we're in the right directory ────────────────────────────
Write-Step "Verifying working directory..."
$expectedFile = ".github\workflows\daily_paper.yml"
if (-not (Test-Path $expectedFile)) {
    Write-Err "Cannot find $expectedFile"
    Write-Err "Please run this script from inside your 'FYP Research' folder:"
    Write-Info "  cd `"C:\Users\varun\Downloads\FYP Research`""
    Write-Info "  .\setup_git.ps1"
    exit 1
}
Write-OK "Correct directory: $(Get-Location)"

# ── Step 3: Configure git identity ───────────────────────────────────────────
Write-Step "Checking git identity..."
$existingName  = git config --global user.name  2>$null
$existingEmail = git config --global user.email 2>$null

if (-not $existingName) {
    $gitName = Read-Host "  Enter your full name for git commits"
    git config --global user.name "$gitName"
    Write-OK "Set user.name = $gitName"
} else {
    Write-OK "user.name already set: $existingName"
}

if (-not $existingEmail) {
    $gitEmail = Read-Host "  Enter your GitHub email address"
    git config --global user.email "$gitEmail"
    Write-OK "Set user.email = $gitEmail"
} else {
    Write-OK "user.email already set: $existingEmail"
}

# ── Step 4: Initialise git repo ───────────────────────────────────────────────
Write-Step "Initialising git repository..."
if (Test-Path ".git") {
    Write-Warn "Git repo already initialised — skipping git init"
} else {
    git init
    Write-OK "Git repo initialised"
}

# Set default branch to main
git checkout -b main 2>$null
if ($LASTEXITCODE -ne 0) {
    git branch -M main
}
Write-OK "Branch set to: main"

# ── Step 5: Stage all files ───────────────────────────────────────────────────
Write-Step "Staging all files..."
git add .
$staged = git diff --staged --name-only
Write-OK "Staged $($staged.Count) files"

# List key files
Write-Info ""
Write-Info "  Key files included:"
$keyFiles = @(
    ".github\workflows\daily_paper.yml",
    ".github\paper-reminder\daily_paper.py",
    ".github\paper-reminder\papers.json",
    ".github\paper-reminder\state.json",
    "README.md",
    ".gitignore"
)
foreach ($f in $keyFiles) {
    if (Test-Path $f) {
        Write-Info "    ✔ $f"
    } else {
        Write-Warn "    ✗ $f (missing)"
    }
}
Write-Info ""

# ── Step 6: Initial commit ────────────────────────────────────────────────────
Write-Step "Creating initial commit..."
$commitMsg = "feat: FYP research repo with daily paper reminder automation

- GitHub Actions workflow: daily Semantic Scholar paper discovery
- Curated papers.json: 30 FYP-relevant papers (GAE, GraphSAGE, eBPF, XDP...)
- Scoring engine: relevance (45%) + recency (25%) + impact (20%) + novelty (10%)
- LaTeX report: Chapters 1-4 full drafts + stub chapters 5-8
- References.bib: 40+ pre-populated BibTeX entries

Fires daily at 09:00 IST (03:30 UTC)"

git commit -m $commitMsg
if ($LASTEXITCODE -ne 0) {
    Write-Warn "Commit failed — possibly nothing staged (repo may already be committed)"
}
Write-OK "Initial commit created"

# ── Step 7: Get GitHub repo URL ───────────────────────────────────────────────
Write-Step "GitHub repository setup..."
Write-Host ""
Write-Host "  You need a GitHub repository to push to." -ForegroundColor White
Write-Host "  If you haven't created one yet:" -ForegroundColor White
Write-Host "    1. Go to https://github.com/new" -ForegroundColor Yellow
Write-Host "    2. Repository name: fyp-ddos-defense  (or any name)" -ForegroundColor Yellow
Write-Host "    3. Visibility: Private (recommended) or Public" -ForegroundColor Yellow
Write-Host "    4. Do NOT initialise with README (we already have one)" -ForegroundColor Yellow
Write-Host "    5. Click 'Create repository'" -ForegroundColor Yellow
Write-Host "    6. Copy the HTTPS URL shown (e.g. https://github.com/VarunRaj004/fyp-ddos-defense.git)" -ForegroundColor Yellow
Write-Host ""

$repoURL = Read-Host "  Paste your GitHub repository HTTPS URL"
$repoURL = $repoURL.Trim()

if ($repoURL -notmatch "^https://github\.com/[^/]+/[^/]+\.git$") {
    if ($repoURL -match "^https://github\.com/[^/]+/[^/]+$") {
        $repoURL = "$repoURL.git"
        Write-Warn "Added .git suffix: $repoURL"
    } else {
        Write-Err "Invalid URL format. Expected: https://github.com/USERNAME/REPO.git"
        exit 1
    }
}

# Extract owner/repo for display
$repoPath = $repoURL -replace "^https://github\.com/" -replace "\.git$"

# ── Step 8: Add remote and push ───────────────────────────────────────────────
Write-Step "Adding remote and pushing..."
$existingRemote = git remote 2>$null
if ($existingRemote -contains "origin") {
    Write-Warn "Remote 'origin' already exists — updating URL"
    git remote set-url origin $repoURL
} else {
    git remote add origin $repoURL
}
Write-OK "Remote origin set to: $repoURL"

Write-Info ""
Write-Info "  Pushing to GitHub... (you may be prompted for credentials)"
Write-Info ""

git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Err "Push failed. Common fixes:"
    Write-Host ""
    Write-Host "  Option A — Use a Personal Access Token (PAT):" -ForegroundColor Yellow
    Write-Host "    1. Go to: https://github.com/settings/tokens/new" -ForegroundColor Gray
    Write-Host "    2. Note: 'FYP repo push', Expiration: 90 days" -ForegroundColor Gray
    Write-Host "    3. Scopes: check 'repo' (full control)" -ForegroundColor Gray
    Write-Host "    4. Generate token — copy it" -ForegroundColor Gray
    Write-Host "    5. When git asks for password, paste the token" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Option B — Use GitHub CLI:" -ForegroundColor Yellow
    Write-Host "    winget install --id GitHub.cli" -ForegroundColor Gray
    Write-Host "    gh auth login" -ForegroundColor Gray
    Write-Host "    git push -u origin main" -ForegroundColor Gray
    exit 1
}

Write-OK "Pushed to GitHub: https://github.com/$repoPath"

# ── Step 9: Enable Actions + print instructions ───────────────────────────────
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "  ║   ✅  SETUP COMPLETE — Your automation is live!             ║" -ForegroundColor Green
Write-Host "  ╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  📋  NEXT STEPS:" -ForegroundColor White
Write-Host ""
Write-Host "  1. Open your repo in a browser:" -ForegroundColor Cyan
Write-Host "     https://github.com/$repoPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "  2. Click the 'Actions' tab — you may see:" -ForegroundColor Cyan
Write-Host "     'I understand my workflows, enable them' → Click it" -ForegroundColor Yellow
Write-Host ""
Write-Host "  3. Trigger your FIRST paper RIGHT NOW:" -ForegroundColor Cyan
Write-Host "     Actions → '📄 Daily Research Paper Reminder (v2)' → 'Run workflow'" -ForegroundColor Yellow
Write-Host ""
Write-Host "  4. In ~30 seconds, check the Issues tab:" -ForegroundColor Cyan
Write-Host "     https://github.com/$repoPath/issues" -ForegroundColor Yellow
Write-Host ""
Write-Host "  5. Enable email notifications (so you get papers every morning):" -ForegroundColor Cyan
Write-Host "     GitHub → Settings → Notifications → Issues: 'Participating and @mentions'" -ForegroundColor Yellow
Write-Host ""
Write-Host "  ⏰  Papers will be suggested automatically at 9:00 AM IST every day." -ForegroundColor Magenta
Write-Host ""
