# Insurance Audit AI — Project Log

**Last updated:** 2026-03-31
**Status:** Production-ready app with autonomous visual QA agent

---

## How to Resume in a New Conversation

Open Claude Code in `C:\Users\Bogdan\Documents\insurance-audits\`. Say:

> "Read PROJECT-LOG.md and CLAUDE.md. Pick up where we left off."

Claude Code reads `CLAUDE.md` automatically on startup. This file (`PROJECT-LOG.md`) gives you current state. Together they are the full context needed to continue without re-explaining anything.

---

## What Has Been Built

### The Application

A multi-page Streamlit app at `insurance-audits/app/`. Run it with `run.bat` or `run.sh` from the `insurance-audits/` folder.

**7 screens (pages/):**

| File | Screen | Purpose |
|------|--------|---------|
| `app.py` | Dashboard | Client cards with policy-type badges, quick stats (policies/findings/critical count, last run date), New Client button |
| `0_Settings.py` | Settings | Broker branding (name, title, company, email, phone), logo upload, signature preview |
| `1_Client_Setup.py` | Client Setup | Create/edit client: industry, revenue, employees, states, upstream contract parties, notes |
| `2_Document_Intake.py` | Document Intake | Upload PDFs/TXTs, view extracted text, manage policy library |
| `3_Analyze.py` | Analyze | Multi-phase AI analysis: individual policy analysis → cross-reference synthesis → findings stored to state |
| `4_Findings_Dashboard.py` | Findings Dashboard | Risk matrix (Program Overview tab), finding cards with Good/Bad/Ugly categorization, severity scoring |
| `5_Report_Builder.py` | Report Builder | Tabs: AM Email, CFO Email, Audit Report, Slide Outline, Export ZIP |
| `6_Strategic_Advisor.py` | Strategic Advisor | CAUA/TBV strategic plan generation, client web research, expander-based rendered output |

**Core modules (core/):**

| File | Purpose |
|------|---------|
| `audit_state.py` | Single source of truth: reads/writes `audit-state.json` per client. `list_clients()` returns policy_type_counts and last_analysis_date for dashboard cards |
| `claude_runner.py` | All Claude Code subprocess calls. Prompt builders for each analysis phase. `_CRITICAL_THINKING_BLOCK` injected into all policy analysis prompts. `run_claude()`, `extract_json()` |
| `pdf_annotator.py` | PyMuPDF-based PDF annotation: highlights policy quotes at exact page/location, saves annotated PDFs to client output folder |
| `pdf_extractor.py` | PyMuPDF text extraction for large PDFs (bypasses base64 limitations) |
| `prompt_generator.py` | Supplementary prompt helpers |
| `report_writer.py` | Markdown report, email draft, slide outline generation from findings state |
| `settings.py` | Loads/saves `insurance-audits/settings.json` (broker branding) |

**Other files:**
- `config.py` — paths, color constants (`COLOR_NAVY`, `COLOR_GOOD`, `COLOR_BAD`, `COLOR_UGLY`)
- `utils.py` — `render_sidebar()`, `inject_css()`, `require_client()`, `render_breadcrumb()`, `render_progress_bar()`. Contains CSS to suppress Streamlit auto-nav (`[data-testid="stSidebarNav"] { display:none }`) and white sidebar text fixes
- `app/assets/` — broker logo storage

### The Autonomous Visual QA Agent

`insurance-audits/auto-agent.py` — runs in a loop to find and fix visual/functional bugs automatically.

**What it does:**
1. Reads `auto-agent-state.json` for known issues (priority ordered)
2. Backs up all `.py` files to `backups/[timestamp]/`
3. Sends fix instruction to Claude Code via `subprocess.run("claude -p --dangerously-skip-permissions")`
4. Runs `py_compile` on all `.py` files — stops after 3 consecutive failures
5. Restarts Streamlit, waits for it to come up
6. Uses Playwright/Chromium to screenshot all 8 pages
7. Sends each screenshot to Anthropic API (`claude-sonnet-4-20250514`) for visual QA
8. New issues discovered by visual QA are appended to the known_issues queue
9. Logs everything to `logs/auto-agent-[timestamp].log`
10. Handles rate limits: 20-min wait for Claude Code, `retry-after` header for Anthropic API

**Safety limits:** max 30 iterations, max 4 hours, 3 consecutive syntax failures = stop, Ctrl+C saves state cleanly.

**Run with:** `run-agent.bat` or `python auto-agent.py --max-iterations 30 --max-hours 4`

**State file:** `auto-agent-state.json` — persists known_issues, resolved_issues, iteration_history across runs.

---

## Architecture Decisions

### Data Model
- **One `audit-state.json` per client** at `clients/[slug]/audit-state.json`. This is the single source of truth. All pages read from it; the Analyze page writes to it.
- **Client slug** = lowercase, hyphens, no spaces (e.g., `rhino-home-services-llc`)
- **`ai-exchange/` folder** per client for all Claude I/O: extracted text, per-policy analysis JSON, cross-reference raw output, strategic-plan cache, client-research cache

### Analysis Pipeline
1. Upload PDFs → PyMuPDF extracts text → saved as `[policy]-extracted.txt` in `ai-exchange/`
2. Per-policy analysis: each policy gets its own Claude call → `[slug]-policy-[name]-analysis.json`
3. Cross-reference synthesis: all policy analyses combined → adjusts finding categories/scores → final `findings` array written to `audit-state.json`
4. Strategic advisor: separate Claude call → `strategic-plan.json` cached in `ai-exchange/`

### Claude Integration
- Claude Code CLI: `claude -p --output-format json` via subprocess stdin
- All prompts injected with `_CRITICAL_THINKING_BLOCK` (15+ rules about NCCI codes, surplus lines, severity calibration, deduplication)
- `extract_json()` handles: direct JSON, `{"result": "..."}` envelope, code fence stripping (` ```json ` prefix)
- Fallback on parse failure: saves raw response, keeps prior findings, shows `st.info()` instead of `st.error()`
- Strategic plan: if `data["raw"]` contains ` ```json\n{...}``` `, strips fences before `json.loads()` — rescues into `cached_plan` for structured rendering

### PDF Annotation
- PyMuPDF (not base64): large policies (3MB+) processed as text files
- Highlights land on correct text by searching for policy quote substring on specified page
- Known issue: highlights sometimes land on page header instead of quoted text (in active fix queue)

### Streamlit Constraints
- Version does not support `icon=` parameter on `st.success()`, `st.info()`, `st.warning()`, `st.error()`, or `st.page_link()`
- Auto-generated sidebar nav hidden via CSS (injected in `utils.py`)
- `st.stop()` inside a tab stops the entire page — must use `if/else` instead
- Signature preview uses `st.code()` for guaranteed visibility in both light/dark themes

### Strategic Plan Rendering
- If `cached_plan` (dict): renders each of 6 known keys as `st.expander()` with recursive `_render_val()`. Script/dialogue content detected and wrapped in blockquote markdown.
- If `cached_raw` (str): split on `## ` headers → expanders with emoji icons by keyword
- Download as `.md`; "Copy to Clipboard" shows `st.code()` in expander

### File Structure
```
insurance-audits/
├── CLAUDE.md                     ← AI brain: methodology, tone, working rules (READ THIS)
├── PROJECT-LOG.md                ← This file: current state, resume instructions
├── auto-agent.py                 ← Autonomous visual QA agent
├── auto-agent-state.json         ← Agent issue queue and iteration history
├── run-agent.bat                 ← Double-click to run the agent
├── run.bat / run.sh              ← Launch the Streamlit app
├── .env                          ← ANTHROPIC_API_KEY (never commit — in .gitignore)
├── .gitignore                    ← Excludes .env, backups/, logs/, client PDFs
├── settings.json                 ← Broker branding (auto-created by app)
├── app/
│   ├── app.py                    ← Dashboard
│   ├── config.py                 ← Paths and color constants
│   ├── utils.py                  ← Sidebar, CSS, shared helpers
│   ├── requirements.txt          ← streamlit, pymupdf, python-docx, pillow, pandas, openpyxl
│   ├── assets/                   ← Broker logo
│   ├── core/                     ← Business logic (see above)
│   └── pages/                    ← 7 Streamlit pages (see above)
├── clients/
│   └── [client-slug]/
│       ├── audit-state.json      ← Client state (single source of truth)
│       ├── client-notes.md       ← Human-readable notes
│       ├── policies/             ← Source PDFs
│       ├── contracts/            ← Upstream contracts
│       ├── output/               ← Annotated PDFs, reports
│       └── ai-exchange/          ← Claude I/O files, caches
├── knowledge-base/               ← Coverage guides, methodology, sample contracts
├── logs/                         ← Agent run logs
└── backups/                      ← Per-iteration .py backups (agent safety net)
```

---

## Test Client: Rhino Home Services, LLC

**Client slug:** `rhino-home-services-llc`
**DBA:** 24 Hour Flood Pros of Albuquerque, LLC
**Industry:** Water damage restoration / environmental abatement / remediation
**States:** NV, FL, TX, AR, GA, UT, KS, AZ (WC policy) — **New Mexico missing despite DBA name**
**Special:** 40+ entities, multi-state operation, environmental abatement contractor

**Policies audited (5 policies, ~400 combined pages):**
- `25-26 WC Berkley RTS Policy.pdf` (87 pages) — Workers Compensation
- `General Liability WIP.pdf` (73 pages) — GL + Contractors Pollution Liability (package)
- `25-26 XS Great Divide Policy.pdf` (18 pages) — Excess/Umbrella
- `25-26 AO Auto Policy - AZ.pdf` — Commercial Auto (Arizona)
- `25-26 AO Auto Policy - UT.pdf` — Commercial Auto (Utah)

**Findings: 35 total**

### UGLY (6 critical — claim would be denied):

| # | Finding | Score | Policy/Page |
|---|---------|-------|-------------|
| 1 | **New Mexico missing from WC policy** — DBA says Albuquerque; NM not in Item 3.A or 3.C | 20 | WC p.11 |
| 2 | **Zero cyber liability** — absolute cyber exclusion on GL, no standalone cyber policy anywhere | 16 | GL p.10 |
| 3 | **Zero EPLI** — no employment practices liability anywhere in 5-policy program; crews enter private residences daily | 16 | GL p.14 |
| 4 | **Total PFAS exclusion** — abatement contractor whose core business is remediation; PFAS trap door on last GL page | 15 | GL p.69 |
| 5 | **Carrier concentration** — same surplus lines carrier (Great Divide) on primary GL and excess; no guaranty fund; excess has no-drop-down provision | 10 | GL p.3; XS p.9 |
| 6 | **WC classification accuracy (Florida)** — class codes may not match actual restoration/abatement operations | 12 | WC p.22 |

### BAD (17 — need attention):
Employers Liability limits at statutory minimum ($100K/$100K/$500K), excess aggregate non-reinstatable across 40+ entities, named insured inconsistency across all 5 policies, WC waiver of subrogation gap, WC classification accuracy (TX and AZ/UT — informational per critical thinking rules 14–15), professional liability prior acts gap, professional liability definition too narrow, bailee's coverage gap at project sites, excess defense costs inside limits, strict currency exhaustion on excess, WOS professional liability gap (Coverage E), NM vehicle territory, pollution transit gap, communicable disease exclusion, known conditions prior work trap, Mexico auto gap.

### GOOD (12 — program does these right):
Blanket additional insured (ongoing + completed ops), P&NC on GL and both auto policies, WOS on GL Coverages A/B/D and both auto policies, CPL core operations coverage, per-project aggregate, HNOA, multi-state WC coverage, vehicle classification accuracy on auto policies, hired auto physical damage, defense costs for Coverage D and E outside limits.

**Strategic plan:** Generated and cached at `ai-exchange/strategic-plan.json`. Contains broker A vs. B script, PCT playbook for all 18 Ugly/Bad findings with laymen titles and presentation sequences, five principals assessment, final meeting outline with opening/closing scripts, mid-meeting trial close, leave-behind summary, progress report agenda.

---

## Known Issues (Agent Fix Queue)

Priority order as loaded in `auto-agent-state.json`:

1. **PDF highlights landing on page header instead of actual quoted text** — PyMuPDF search finding the wrong text instance on the page
2. **Strategic advisor displaying raw JSON instead of formatted sections** — Fixed in session ending 2026-03-31; code-fence rescue logic added. Verify fix is working.
3. **Settings signature preview text not visible against dark background** — Fixed with `st.code()`; verify
4. **Risk matrix score numbers showing in empty cells** — Should only show numbers in cells that have findings
5. **Risk matrix should be on Program Overview tab not Critical tab** — Fixed; verify
6. **WHAT THIS MEANS FOR THE BUSINESS text invisible in finding cards** — Color contrast issue
7. **RECOMMENDATION text invisible in finding cards** — Color contrast issue
8. **Cross-reference step JSON parse failures** — Graceful fallback added; verify no edge case regressions
9. **Slide outline generator still crashes on None values** — `5_Report_Builder.py`
10. **WC class code 9014 findings should be Informational not Ugly** — Update prompts and re-classify (CLAUDE.md rule 14 already added; analysis prompt needs reinforcement)
11. **Surplus lines findings should be Informational not critical** — Same as above (CLAUDE.md rule 15 already added)
12. **Deduplicate findings that appear across multiple states** — Same finding in FL/TX/AZ should be ONE finding with multi-state note (CLAUDE.md rule 18 already added; verify synthesis prompt enforces it)

---

## API Key Situation — ACTION REQUIRED

The `ANTHROPIC_API_KEY` in `.env` was created during the session on 2026-03-31 and has been exposed in this conversation. **Rotate it before running the agent.**

1. Go to https://console.anthropic.com → API Keys
2. Create a new key
3. Replace the value in `insurance-audits/.env`
4. The old key should be revoked

The `.env` file is excluded from git via `.gitignore`. Do not commit it.

---

## CLAUDE.md Critical Thinking Rules (current as of 2026-03-30)

Rules 1–13 cover the core audit methodology. **Rules 14–18 were added 2026-03-30** to prevent over-flagging:

- **Rule 14:** NCCI class code 9014 — don't flag by phraseology alone; the code covers multiple types of cleaning/restoration regardless of label. Flag for verification, not as an error. Category: Informational.
- **Rule 15:** Surplus lines / E&S placement is not a critical finding by itself. Only flag if there's genuine carrier concentration (same carrier on primary AND excess) or if the risk could reasonably be placed admitted.
- **Rule 16:** Severity calibration — Ugly = real claim denied with zero coverage. Bad = gap needing attention. Informational = needs verification. Don't drift items up.
- **Rule 17:** Quality over quantity — 15 precise findings beat 35 padded ones. If it's really "verify with carrier," it's Informational.
- **Rule 18:** Cross-state dedup — one finding for FL/TX/AZ issues, not three separate findings.

---

## Broker Settings

**Bogdan Laza, CLCS**
Strategic Risk Consultant | Property & Casualty
Patriot Growth Insurance Services
Bogdan.Laza@PatriotGIS.com | (503) 869-5691

---

## Tech Stack

- **Python:** Anaconda at `C:\Users\Bogdan\anaconda3\python.exe`
- **Streamlit:** `>=1.36.0`
- **PyMuPDF:** PDF text extraction and annotation
- **Claude Code CLI:** `claude -p --output-format json` via subprocess
- **Anthropic SDK:** `anthropic` Python package (for auto-agent visual QA)
- **Playwright:** Chromium browser automation (for auto-agent screenshots)
- **Platform:** Windows 10 Home, VS Code or terminal

---

## Session History (major milestones)

| Date | What was built |
|------|----------------|
| 2026-03-24 | Project created, CLAUDE.md written, folder structure established |
| 2026-03-24 | First policy audit run (manual Claude Code session) |
| 2026-03-25 | Streamlit app scaffolded: all 7 pages, core modules, dashboard |
| 2026-03-25 | Rhino Home Services loaded as test client; 5 policies analyzed |
| 2026-03-27 | Critical thinking rules 1–13 added to CLAUDE.md; NCCI/surplus lines guidance |
| 2026-03-27 | PDF annotator built; Report Builder built; Export ZIP added |
| 2026-03-28 | Strategic Advisor page built; CAUA/TBV prompt framework |
| 2026-03-30 | Critical thinking rules 14–18 added; analysis prompts reinforced with `_CRITICAL_THINKING_BLOCK` |
| 2026-03-30 | Multiple bug fixes: syntax error in Findings Dashboard, cross-reference fallback, sidebar cleanup, text visibility |
| 2026-03-30 | Strategic Advisor JSON rendering fixed: code-fence rescue, expander-based recursive renderer |
| 2026-03-30 | Risk matrix moved to Program Overview tab; score numbers only in non-empty cells |
| 2026-03-31 | Autonomous visual QA agent built: `auto-agent.py`, Playwright, Anthropic API integration |
| 2026-03-31 | `.env`, `.gitignore` created; Playwright + anthropic installed |

---

## Decisions Made

- Using Claude Code CLI (not API directly) for policy analysis — richer reasoning, longer context
- Anaconda Python, not system Python
- Single `audit-state.json` per client (not a database)
- PyMuPDF for PDF processing (not base64 — large files exceed limits)
- Streamlit multi-page app (pages numbered 0–6 for sidebar ordering)
- All report output as Markdown (portable, renderable, downloadable)
- `ai-exchange/` folder pattern for Claude I/O isolation per client
- Strategic plan cached as JSON (or raw fallback) — never re-generated unless button clicked
- Auto-agent uses `claude -p --dangerously-skip-permissions` to allow file edits without prompts
