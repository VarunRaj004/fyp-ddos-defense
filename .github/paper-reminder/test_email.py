#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_email.py
-------------
1. Generates the full HTML email from a real paper selection
2. Saves it as email_preview.html and opens in your browser
3. Optionally sends a real test email via Gmail SMTP

Run:
  py -X utf8 .github\paper-reminder\test_email.py

To send a real email, set these env vars first in PowerShell:
  $env:GMAIL_USER         = "yourname@gmail.com"
  $env:GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
  $env:RECIPIENT_EMAIL    = "yourname@gmail.com"
  py -X utf8 .github\paper-reminder\test_email.py
"""

import sys, io, os, json, webbrowser, tempfile, datetime, smtplib
sys.path.insert(0, os.path.dirname(__file__))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from daily_paper import (
    load_state,
    select_from_semantic_scholar,
    select_from_curated,
    build_email_html,
    send_email,
    format_issue_title,
)

PREVIEW_FILE = os.path.join(os.path.dirname(__file__), "email_preview.html")

# ── colours ──────────────────────────────────────────────────────────────────
G = "\033[92m"; R = "\033[91m"; Y = "\033[93m"; C = "\033[96m"
B = "\033[1m";  D = "\033[2m";  X = "\033[0m"

def sep(title=""):
    print(f"\n{B}{C}{'='*60}{X}")
    if title: print(f"{B}{C}  {title}{X}")

# ─────────────────────────────────────────────────────────────────────────────
print(f"\n{B}{'='*60}")
print(f"  FYP Paper Reminder -- Email Test")
print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*60}{X}")

# ── STEP 1: Select a paper ────────────────────────────────────────────────────
sep("STEP 1  -- Select paper")
state = load_state()

print(f"  {Y}Trying Semantic Scholar API...{X}")
paper = select_from_semantic_scholar(state)

if paper:
    print(f"  {G}[OK]{X}  Live paper found")
    print(f"       Source  : Semantic Scholar")
    print(f"       Score   : {paper.get('score')}")
else:
    print(f"  {Y}[WARN]{X}  API unavailable -- using curated fallback")
    paper = select_from_curated(state)
    print(f"  {G}[OK]{X}  Curated paper selected (id #{paper.get('id')})")

print(f"\n  {B}Selected paper:{X}")
print(f"  Title    : {paper['title'][:70]}")
print(f"  Authors  : {paper.get('authors','')[:55]}")
print(f"  Year     : {paper.get('year','?')}")
print(f"  Priority : {paper.get('priority','?')}")
print(f"  Category : {paper.get('category','?')}")

# ── STEP 2: Render HTML email ─────────────────────────────────────────────────
sep("STEP 2  -- Render HTML email")

fake_issue_url = "https://github.com/YOUR_USERNAME/fyp-ddos-defense/issues/1"
html = build_email_html(paper, state, fake_issue_url)

with open(PREVIEW_FILE, "w", encoding="utf-8") as f:
    f.write(html)

size_kb = os.path.getsize(PREVIEW_FILE) / 1024
print(f"  {G}[OK]{X}  HTML generated  ({size_kb:.1f} KB)")
print(f"       Saved to: {PREVIEW_FILE}")

# Check key sections exist
checks = ["TL;DR", "Reading Checklist", "MUST READ TODAY|HIGH PRIORITY|MEDIUM PRIORITY|LOW PRIORITY",
          "Semantic Scholar|Curated", "FYP Daily Paper Reminder"]
all_ok = True
for check in checks:
    import re
    found = any(c in html for c in check.split("|"))
    status = f"{G}[OK]{X}" if found else f"{R}[MISSING]{X}"
    label  = check.split("|")[0] + ("..." if "|" in check else "")
    print(f"  {status}  Contains '{label}'")
    if not found: all_ok = False

# ── STEP 3: Open in browser ───────────────────────────────────────────────────
sep("STEP 3  -- Open email preview in browser")
try:
    file_uri = "file:///" + PREVIEW_FILE.replace("\\", "/")
    webbrowser.open(file_uri)
    print(f"  {G}[OK]{X}  Opened in browser: {file_uri}")
except Exception as e:
    print(f"  {Y}[WARN]{X}  Could not auto-open browser: {e}")
    print(f"       Manually open: {PREVIEW_FILE}")

# ── STEP 4: SMTP connectivity test ───────────────────────────────────────────
sep("STEP 4  -- Gmail SMTP test")

gmail_user = os.environ.get("GMAIL_USER", "").strip()
gmail_pass = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
recipient  = os.environ.get("RECIPIENT_EMAIL", "").strip() or gmail_user

if not gmail_user or not gmail_pass:
    print(f"  {Y}[SKIP]{X}  Email credentials not set in environment")
    print(f"")
    print(f"  To send a REAL test email, run in PowerShell:")
    print(f"")
    print(f"    {C}$env:GMAIL_USER         = \"yourname@gmail.com\"{X}")
    print(f"    {C}$env:GMAIL_APP_PASSWORD = \"xxxx xxxx xxxx xxxx\"{X}")
    print(f"    {C}$env:RECIPIENT_EMAIL    = \"yourname@gmail.com\"{X}")
    print(f"    {C}py -X utf8 .github\\paper-reminder\\test_email.py{X}")
    print(f"")
    print(f"  {D}  (App Password: myaccount.google.com/apppasswords){X}")
else:
    print(f"  {G}[OK]{X}  Credentials found")
    print(f"       Sender    : {gmail_user}")
    print(f"       Recipient : {recipient}")

    # Test SMTP connection first (without sending)
    print(f"\n  {Y}Testing SMTP connection to smtp.gmail.com:465 ...{X}")
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as s:
            code, msg = s.login(gmail_user, gmail_pass)
            print(f"  {G}[OK]{X}  SMTP login successful (code {code})")
    except smtplib.SMTPAuthenticationError:
        print(f"  {R}[FAIL]{X}  Authentication failed")
        print(f"         Make sure you used an APP PASSWORD, not your Google login password.")
        print(f"         Get one at: myaccount.google.com/apppasswords")
        sys.exit(1)
    except Exception as e:
        print(f"  {R}[FAIL]{X}  Connection error: {e}")
        sys.exit(1)

    # Send the real test email
    print(f"\n  {Y}Sending test email...{X}")
    sent = send_email(paper, state, fake_issue_url)
    if sent:
        print(f"  {G}[OK]{X}  Email sent to {recipient}")
        print(f"       Check your inbox -- subject starts with today's date")
        print(f"       {D}(Check Spam folder if not in inbox){X}")
    else:
        print(f"  {R}[FAIL]{X}  Email sending failed -- see error above")

# ── Summary ───────────────────────────────────────────────────────────────────
sep("SUMMARY")
print(f"""
  Paper selected  : {G}YES{X}  ({paper.get('source','curated')})
  HTML rendered   : {G}YES{X}  ({size_kb:.1f} KB)
  Browser preview : {G}OPENED{X}
  Email sending   : {G + 'SENT' + X if (gmail_user and gmail_pass) else Y + 'SKIPPED (set env vars)' + X}

  {B}Preview file:{X}  {PREVIEW_FILE}
""")

if all_ok:
    print(f"  {G}{B}All checks passed. System is working correctly.{X}")
else:
    print(f"  {R}{B}Some checks failed -- review output above.{X}")
print()
