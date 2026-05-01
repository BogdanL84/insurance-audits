# Insurance Audit System — Full Project Handoff v2
## For continuing in a new Claude conversation
**Last updated:** April 21, 2026
**Project owner:** Bogdan Laza, CLCS — Strategic Risk Consultant, Patriot Growth Insurance Services

---

## WHAT THIS IS

An AI-powered commercial insurance audit application built with Python/Streamlit running locally on Bogdan's Windows PC. It analyzes commercial P&C policies, identifies coverage gaps, cross-references the full program, and produces strategic sales positioning using the CAUA/TBV methodology.

**Core value proposition:** Replaces the manual Excel-based RMF (Risk Mitigation Factor) analysis process with an AI-powered system that reads policies, finds gaps, and generates client-ready findings with page-level citations.

---

## WHERE EVERYTHING LIVES

**All project files:** `C:\Users\Bogdan\Documents\insurance-audits\`

```
insurance-audits/
├── CLAUDE.md                    ← Master methodology file (read every session)
├── HANDOFF-COMPLETE.md          ← Original handoff (v1, March 2026)
├── HANDOFF-v2.md                ← THIS FILE
├── settings.json                ← Broker branding
├── run.bat                      ← Double-click to launch Streamlit app
├── .env                         ← Anthropic API key (for future use)
├── app/
│   ├── app.py                   ← Dashboard (home screen)
│   ├── config.py                ← Paths, colors, constants
│   ├── utils.py                 ← Sidebar, CSS, progress bar (6 steps)
│   ├── core/
│   │   ├── audit_state.py       ← JSON state management per client
│   │   ├── pdf_extractor.py     ← PyMuPDF text extraction
│   │   ├── claude_runner.py     ← Subprocess calls to Claude Code + KB loader
│   │   └── report_writer.py     ← Report generators
│   └── pages/
│       ├── 0_Settings.py        ← Broker branding
│       ├── 1_Client_Setup.py    ← Create/edit client profiles
│       ├── 2_Document_Intake.py ← Upload policies/contracts, view status
│       ├── _Analyze.py          ← Policy queue + synthesize (Step 3)
│       ├── 3_Findings_Dashboard.py ← View/edit findings
│       ├── 4_Strategic_Advisor.py  ← CAUA strategic plan
│       └── _Report_Builder.py   ← Reports, emails, slide outlines
├── knowledge-base/
│   └── by-coverage/
│       ├── gl/                  ← 5 PDFs + 00_RMF-checklist.md + 00_universal-checklist.md
│       ├── auto/                ← 5 PDFs + 00_RMF-checklist.md + 00_universal-checklist.md
│       ├── property/            ← 5 PDFs + 00_RMF-checklist.md + 00_universal-checklist.md
│       ├── umbrella-excess/     ← 5 PDFs + 00_RMF-checklist.md + 00_universal-checklist.md
│       ├── inland-marine/       ← 1 PDF + 00_RMF-checklist.md + 00_universal-checklist.md
│       ├── workers-comp/        ← 5 PDFs + 00_RMF-checklist.md + 00_universal-checklist.md
│       ├── cyber/               ← 01_cyber-coverage-cheat-sheet.pdf
│       ├── do-epli/             ← 01_DO-coverage-cheat-sheet.pdf + 02_EPLI-coverage-cheat-sheet.pdf
│       ├── professional-liability/ ← 01_EO-coverage-cheat-sheet.pdf
│       ├── pollution/           ← 2 PDFs
│       └── contracts/           ← 00_client-facing-descriptions.md + top 10 scariest terms PDF
└── clients/
    └── [client-slug]/
        ├── policies/            ← uploaded PDFs
        ├── contracts/           ← uploaded contract PDFs
        ├── ai-exchange/         ← extracted text + analysis JSONs + findings JSON
        └── audit-state.json     ← all client state
```

---

## ARCHITECTURE — HOW IT WORKS

### Tech Stack
- **Streamlit** — web UI at localhost:8501
- **Claude Code** (`claude --dangerously-skip-permissions -p --output-format json`) — called via Python subprocess for all AI analysis. Uses Bogdan's Claude Pro subscription.
- **PyMuPDF (fitz)** — PDF text extraction with PAGE N of M markers
- **JSON files** — all state stored per-client, no database

### The 4-Step Analysis Pipeline
```
1. EXTRACT   → PyMuPDF reads PDF → saves {stem}-extracted.txt in ai-exchange/
               Fast, local, no Claude tokens used

2. READ POLICY → Claude Code analyzes one policy at a time
               Chunked at 80k chars on page boundaries
               Saves {slug}-policy-{stem}-analysis.json immediately
               Uses tokens — WC policy = ~11 chunks = ~11 Claude calls

3. SYNTHESIZE → "Review Full Program" button
               Loads all existing analysis JSONs from ai-exchange/
               One Claude call to cross-reference the whole program
               Produces final findings with Good/Bad/Ugly/Review categories

4. FINDINGS  → Displayed in Findings Dashboard
               Tabs: Critical / Bad / Good / All / By Policy / What Changed / History
```

### Knowledge Base Loading
`_load_kb_for_policy_type()` in `claude_runner.py`:
- Detects policy type from filename or analysis JSON
- Loads matching folder from `knowledge-base/by-coverage/[type]/`
- Loads **both .pdf AND .md files** (recently updated)
- Files starting with `00_` sort first (RMF checklists load before other content)
- Max 5 files, 5,000 chars per file, 15,000 chars total per analysis call

---

## CURRENT STATE — WHAT WORKS

### ✅ Fully Working
- Dashboard with client cards, stats, Good/Bad/Ugly counts
- Client Setup — full profile (name, industry, revenue, states, risk flags)
- Document Intake — upload PDFs, auto-extract text, shows Extracted/Analyzed/Failed status per policy
- Per-policy "Read Policy" / "Re-read Policy" buttons on Document Intake page
- Analyze page (Step 3) — policy queue table with checkboxes, chunk estimates, status badges
- "Review Full Program" button — synthesis-only mode, loads existing analysis JSONs
- Rate limit detection — detects "out of extra usage" and labels errors as RATE_LIMIT:
- Findings Dashboard — Critical/Bad/Good tabs, page citations, green "Covered by" cross-reference box
- Progress bar navigation — 6 steps: Setup → Upload → Analyze → Findings → Strategic Advisor → Report
- Sidebar navigation — all 5 pages linked
- Knowledge base — RMF checklists in every coverage folder, cyber/D&O/E&O/EPLI cheat sheets

### ⚠️ Known Issues / Partially Working
- **Synthesis freezes with no progress indicator** — the synthesis call runs but the timer shows 0m 0s. It does eventually complete (took ~1 hour in last test) but there's no visible feedback. Need better progress display.
- **Rate limit stop-immediately not fully working** — detects rate limit (shows RATE_LIMIT: prefix) but continues attempting remaining policies instead of stopping. Burns through failed calls.
- **Orphan findings cleanup over-aggressive** — when findings load, it removes findings whose policy files it thinks are "no longer uploaded" even when they are. Needs fix to exact filename matching.
- **Italic text rendering bug** — some technical analysis text has words merged together (no spaces) in italic sections. Caused by LaTeX-style formatting in Claude's output. Needs markdown cleanup.
- **Discovery Questions placeholder** — shows "Re-run analysis to generate discovery questions" instead of hiding when empty.
- **Strategic Advisor** — may still display raw JSON in some cases (was a known bug from v1).
- **WC chunking** — WC policy (994k chars) generates 14 chunks and uses a full day's tokens alone. WC fast-scan mode (larger chunks + targeted prompt) was discussed but not yet built.

### ❌ Not Yet Built
- Per-policy analyze button from Document Intake page with live timer (was requested, prompt written but Claude Code may have frozen)
- WC fast-scan mode (150k chunks + targeted 7-point checklist only)
- ZIP export of full audit package
- Program Overview tab (policy summary table with carrier/limits/premium/dates)
- Audit history comparison (what changed between runs)

---

## RECENT MAJOR CHANGES (this session)

### Knowledge Base — Massive Upgrade
Previously: 3 coverage folders had ZERO reference material (cyber, D&O/EPLI, professional liability). GL folder was loading 4 overlapping "Additional Insured" files and missing WOS, P&NC, and the annotated CGL form.

Now:
1. **GL folder renamed** — top 5 files now: AI cheat sheet, annotated CG0001, contractual liability, WOS, primary-noncontributory
2. **Cyber cheat sheet created** — 2-page PDF covering retroactive dates, ransomware sublimits, social engineering, BI triggers, nation-state exclusion
3. **D&O cheat sheet created** — Side A/B/C, IvI exclusion carve-outs, bump-up exclusion, investigation costs
4. **EPLI cheat sheet created** — Employee definition, third-party harassment, wage & hour, hammer clause
5. **E&O cheat sheet created** — Claims-made mechanics, prior acts gaps, professional services definition, subcontractor coverage
6. **WC fast-scan cheat sheet created** — 7-point checklist only (covered states, class codes, EMOD, EL limits, WOS, cancellation notice, named insured). Includes "What NOT to Flag on WC" section.
7. **RMF checklists extracted from Excel** — Full checklist for GL (33 questions), Auto (18), Property (31), Umbrella (14), Inland Marine (14), WC (16), Universal (5). Saved as markdown in each coverage folder.
8. **Client-facing descriptions** — 30 plain-English finding explanations saved to contracts/ folder
9. **KB loader updated** — now reads .md files as well as PDFs, 00_ files sort first

### Findings Display — Fixed
- Text truncation bug fixed: `[:120]` slice on `gap_description` in compressed_findings dict was corrupting stored findings during cross-policy pass
- Policy citation (filename + page) now shows ABOVE technical analysis text
- Risk score (12/25 Medium L:4×S:3) removed from display — was noise
- Green "Covered by" box styling kept — well received
- Full text now displays without truncation

### UI Navigation — Fixed
- "Analyze" added as Step 3 in progress bar
- All 5 pages now appear in sidebar
- "Go to Analyze →" button added to bottom of Document Intake
- "Review Full Program" button prominent at top of Analyze page
- Document Intake cleaned up — removed Re-extract button, removed Re-run Analysis button

### Findings Logic — Improved
- New "Review" category added — amber/yellow badge for findings where coverage is uncertain
- Severity reclassification rules added to synthesis prompt:
  - Full coverage elsewhere → Good
  - Partial coverage elsewhere → stays Ugly/Bad with partial_coverage_note
  - Uncertain → Review category
- covered_by_page field added to cross-reference citations

---

## UPCOMING WORK (priority order)

### Immediate Fixes Needed
1. **Fix synthesis progress indicator** — show live elapsed timer, don't show 0m 0s while running
2. **Fix rate limit stop-immediately** — when RATE_LIMIT detected on any call, stop all further Claude calls instantly, show reset time, save what's done
3. **Fix orphan findings false positives** — exact filename matching only
4. **Fix italic text spacing** — clean LaTeX/markdown artifacts before rendering
5. **Hide empty Discovery Questions section**

### Next Features
6. **WC fast-scan mode** — detect WC policies, use 150k chunk size, inject only the 7-point WC cheat sheet
7. **Per-policy analyze button with timer** — on Document Intake, "Read Policy" button that shows live elapsed time (was requested, prompt written but not confirmed working)
8. **Strategic Advisor JSON display fix** — ensure formatted output not raw JSON
9. **Program Overview tab** — policy summary table

### Training Material Still Pending
The following files were uploaded at end of session but NOT yet processed into knowledge base:
- `The_Messina_Method.docx` — sales presentation framework (→ methodology/)
- `top_10_scariest_insurance_policy_terms.pdf` — SDV attorney list (→ contracts/)
- `PFC-D_-_Process_Flow_Chart_Diary.xlsx` — process flow diary
- `PFC-K_-_Process_Flow_Chart_KEY.pdf` — 7-step process flow (already read, → methodology/)
- `8E-Qualification_Criteria.xlsx` — 18 qualification questions
- `8D-Final_Meeting_Outline.docx` — final meeting structure
- `8A-Winning_the_Account.docx` — account strategy framework
- `8B-Connecting_with_Your_Customer.docx` — PCT presentation prep (10 questions per finding)
- `8C-Creating_the_Final_Strategy.docx` — strategy creation framework
- `BB_Retail_Detailed_Template.pptx` — presentation template
- `5-LED_Example.xlsx` — LED (Limits/Exposure/Deductible) comparison example
- `3-Seeking_to_Understand_AKA__Strategic_Questions.xlsx` — 126-row strategic questions list

**These should be extracted into markdown training files and placed in:**
- Sales/methodology content → `knowledge-base/methodology/`
- The strategic questions list is especially valuable — it's the full conference call question bank

---

## TOKEN MANAGEMENT — CRITICAL CONTEXT

Bogdan uses **Claude Pro ($20/month)**. The analysis engine calls `claude -p` as a subprocess, which shares the same usage pool as claude.ai chat.

**Usage realities:**
- Claude Pro resets every ~5 hours (rolling window), hard reset daily around 2pm Phoenix time
- WC policy alone = 14 chunks + 1 merge = ~15 Claude calls = likely hits daily limit
- Recommended workflow: analyze 2-3 policies per session, synthesize when all are done
- Rate limit error message: `"You're out of extra usage · resets Xpm (America/Phoenix)"`

**Upgrade option:** Claude Max at $100/month gives 5x usage — would allow full program analysis in one session.

---

## TEST CLIENT

**Run-Test Election Services** (slug: `run-test-election-services`)
- Industry: Manufacturing (election services/ballot printing)
- 4 contracts uploaded (LA County, Douglas County CO, Sacramento, Maricopa)
- 10 policies: WC (2 versions), Management Liability, Professional Liability (E&O), Security Guards GL, Excess Tech E&O, Cyber (AmTrust), Commercial Auto, Commercial Package, Commercial Umbrella
- Current findings: 27 (as of last synthesis) — 3-4 critical, 11-16 bad, 5-8 good
- Notable findings: cyber retroactive date gap, no umbrella over E&O tower, D&O manufacturing exclusion bars entity coverage, delay in performance exclusion on E&O

---

## HOW TO RESUME

### In Claude Code (for code changes)
```
cd C:\Users\Bogdan\Documents\insurance-audits
claude
```
Then paste your prompt. Keep prompts under ~800 chars to avoid PowerShell truncation — use multiple messages for complex changes.

### In claude.ai (for planning/discussion)
Upload this HANDOFF-v2.md and say:
"I'm continuing my insurance audit app project. Read this handoff carefully then tell me what you understand and ask what I want to work on."

### To run the app
Double-click `run.bat` in `C:\Users\Bogdan\Documents\insurance-audits\`
App runs at `localhost:8501`

---

## TECHNICAL GOTCHAS

- Streamlit version on Bogdan's machine does NOT support emoji `icon=` parameter
- All `.get("field", "").strip()` must use `str(f.get("field", "") or "").strip()` to handle None
- Claude Code subprocess uses `shell=True` with prompt via `stdin`
- Timeout per Claude call: 1800 seconds (30 min)
- PyMuPDF needed for PDF extraction AND KB loading — both use fitz
- PowerShell paste limit: ~800 chars before truncation. Break long prompts into chunks.
- The Analyze page file is named `_Analyze.py` (with underscore) — Streamlit uses this to hide it from the default sidebar while still allowing `st.switch_page()` navigation to it

---

## BOGDAN'S PREFERENCES

- Direct, no fluff — if something is broken say so
- One app, one flow — hates multi-step workflows
- Presentation style: "The Good, The Bad, The Ugly" with dog meme dividers
- Evidence-based: contract language vs policy language side-by-side  
- CFO-friendly: no jargon without explanation
- Page references on EVERY finding
- Humor: "Dewey, Cheetham & Howe" reference
- Does NOT want: risk scores displayed (noise), empty placeholder sections, buttons that do nothing visible
- DOES want: live timers on long operations, clear status on every policy, ability to run one policy at a time
