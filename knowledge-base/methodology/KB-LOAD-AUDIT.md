# KB Load Audit — Which Files Does the Pipeline Actually Read?

**Audit date:** 2026-04-29 · **Total files in `knowledge-base/`:** 228 · **Loaded by pipeline:** 49 (21%) · **Orphaned:** 179 (78%)

**Total size on disk:** 859,262 KB · **Loaded size:** 31,335 KB (4%)

## Pipeline load rules (for reference)

From `app/core/claude_runner.py:_load_kb_for_policy_type`:

```
Per per-policy analysis prompt, four sources concatenated:
  1. by-coverage/[detected-type]/  → top 6 .md/.pdf, sorted (00_ first, then alphabetical)
  2. universal/                     → top 6 .md/.pdf
  3. methodology/                   → top 3 .md/.pdf
  4. contracts/                     → top 2 .md/.pdf
Per-file cap: 7,500 chars. Total budget: 50,000 chars.

Plus specific reads:
  - methodology/CAUA-framework-summary.md → Strategic Advisor prompt
  - universal/GAP-01, GAP-17, GAP-20, GAP-21 → cross-policy matrix prompt

NEVER loaded:
  - .docx, .doc, .pptx, .xlsx, .png, .jpg, .html files
  - Files in archive/ or any other subfolder of a load folder
  - knowledge-base/ root files
  - knowledge-base/strategic/ and knowledge-base/presentations/
```


## LOADED — 49 files (31,335 KB)

| File | Size (KB) | Why |
|---|---:|---|
| `by-coverage/auto/00_RMF-checklist.md` | 4 | per-policy KB injection (auto), slot 1/6 |
| `by-coverage/auto/Auto policy marked up.pdf` | 260 | per-policy KB injection (auto), slot 2/6 |
| `by-coverage/auto/GAP-19-named-driver-exclusions.md` | 4 | per-policy KB injection (auto), slot 3/6 |
| `by-coverage/auto/Insuring Hired Autos for Liability and Physical Damage.pdf` | 1026 | per-policy KB injection (auto), slot 4/6 |
| `by-coverage/auto/Insuring personally owned vehicles on the BAP.pdf` | 650 | per-policy KB injection (auto), slot 5/6 |
| `by-coverage/auto/MCS-90 newsletter_2013winter_commercial_trans authcheckdam.pdf` | 415 | per-policy KB injection (auto), slot 6/6 |
| `by-coverage/cyber/01_cyber-coverage-cheat-sheet.pdf` | 6 | per-policy KB injection (cyber), slot 1/6 |
| `by-coverage/cyber/GAP-22-cyber-dec-sheet-patterns.md` | 8 | per-policy KB injection (cyber), slot 2/6 |
| `by-coverage/do-epli/01_DO-coverage-cheat-sheet.pdf` | 6 | per-policy KB injection (do-epli), slot 1/6 |
| `by-coverage/do-epli/02_EPLI-coverage-cheat-sheet.pdf` | 6 | per-policy KB injection (do-epli), slot 2/6 |
| `by-coverage/gl/00_RMF-checklist.md` | 9 | per-policy KB injection (gl), slot 1/6 |
| `by-coverage/gl/01_AI-cheat-sheet.pdf` | 108 | per-policy KB injection (gl), slot 2/6 |
| `by-coverage/gl/02_CG0001-annotated.pdf` | 1054 | per-policy KB injection (gl), slot 3/6 |
| `by-coverage/gl/03_CGL-contractual-liability.pdf` | 3947 | per-policy KB injection (gl), slot 4/6 |
| `by-coverage/gl/04_WOS.pdf` | 148 | per-policy KB injection (gl), slot 5/6 |
| `by-coverage/gl/05_primary-noncontributory.pdf` | 371 | per-policy KB injection (gl), slot 6/6 |
| `by-coverage/inland-marine/00_RMF-checklist.md` | 3 | per-policy KB injection (inland-marine), slot 1/6 |
| `by-coverage/inland-marine/INLAND MARINE.pdf` | 8671 | per-policy KB injection (inland-marine), slot 2/6 |
| `by-coverage/pollution/Amwins pollution.pdf` | 203 | per-policy KB injection (pollution), slot 1/6 |
| `by-coverage/pollution/CG 2149 0999 Total Pollution Exclusion.pdf.pdf` | 52 | per-policy KB injection (pollution), slot 2/6 |
| `by-coverage/professional-liability/01_EO-coverage-cheat-sheet.pdf` | 6 | per-policy KB injection (professional-liability), slot 1/6 |
| `by-coverage/property/00_RMF-checklist.md` | 6 | per-policy KB injection (property), slot 1/6 |
| `by-coverage/property/05_business-income.pdf` | 796 | per-policy KB injection (property), slot 2/6 |
| `by-coverage/property/CP 00 10 10 12 Coverage Form (marked up).pdf` | 1008 | per-policy KB injection (property), slot 3/6 |
| `by-coverage/property/CP 10 30 10 12 - Causes of Loss (marked up).pdf` | 540 | per-policy KB injection (property), slot 4/6 |
| `by-coverage/property/edp versus property.pdf` | 143 | per-policy KB injection (property), slot 5/6 |
| `by-coverage/property/Ordinance or Law Insurance Coverage.pdf` | 2484 | per-policy KB injection (property), slot 6/6 |
| `by-coverage/umbrella-excess/00_RMF-checklist.md` | 3 | per-policy KB injection (umbrella-excess), slot 1/6 |
| `by-coverage/umbrella-excess/01_concurrency-issues.pdf` | 136 | per-policy KB injection (umbrella-excess), slot 2/6 |
| `by-coverage/umbrella-excess/Book of Solutions Umbrella.pdf` | 4263 | per-policy KB injection (umbrella-excess), slot 3/6 |
| `by-coverage/umbrella-excess/GAP-08-umbrella-structure.md` | 7 | per-policy KB injection (umbrella-excess), slot 4/6 |
| `by-coverage/umbrella-excess/Horizontal Exhaustion.pdf` | 127 | per-policy KB injection (umbrella-excess), slot 5/6 |
| `by-coverage/umbrella-excess/Umbrella Condition - Maintenance of underlying policies.pdf` | 3160 | per-policy KB injection (umbrella-excess), slot 6/6 |
| `by-coverage/workers-comp/00_RMF-checklist.md` | 3 | per-policy KB injection (workers-comp), slot 1/6 |
| `by-coverage/workers-comp/01_WC-fast-scan-cheat-sheet.pdf` | 7 | per-policy KB injection (workers-comp), slot 2/6 |
| `by-coverage/workers-comp/TRIA-Terrorism-Coverage-WC.pdf` | 746 | per-policy KB injection (workers-comp), slot 3/6 |
| `by-coverage/workers-comp/WC-Retro-Rating-Plans-McNerney.pdf` | 895 | per-policy KB injection (workers-comp), slot 4/6 |
| `contracts/00_client-facing-descriptions.md` | 4 | per-policy KB injection (contracts block), slot 1/2 |
| `contracts/00_top10-scary-terms.md` | 3 | per-policy KB injection (contracts block), slot 2/2 |
| `methodology/00_messina-method.md` | 1 | per-policy KB injection (methodology block), slot 1/3 |
| `methodology/01_process-flow-chart.md` | 2 | per-policy KB injection (methodology block), slot 2/3 |
| `methodology/02_qualification-criteria.md` | 1 | per-policy KB injection (methodology block), slot 3/3 |
| `methodology/CAUA-framework-summary.md` | 11 | loaded by claude_runner._load_caua_summary() for Strategic Advisor prompt |
| `universal/GAP-01-named-insured-verification.md` | 6 | per-policy KB injection (universal block), slot 1/6; ALSO loaded by cross_policy.load_universal_kb_block() |
| `universal/GAP-02-cancellation-notice-verification.md` | 6 | per-policy KB injection (universal block), slot 2/6 |
| `universal/GAP-17-contract-specific-coverage-satisfaction.md` | 5 | per-policy KB injection (universal block), slot 3/6; ALSO loaded by cross_policy.load_universal_kb_block() |
| `universal/GAP-18-coverage-specific-sublimits.md` | 5 | per-policy KB injection (universal block), slot 4/6 |
| `universal/GAP-20-cross-policy-named-insured-inconsistency.md` | 6 | per-policy KB injection (universal block), slot 5/6; ALSO loaded by cross_policy.load_universal_kb_block() |
| `universal/GAP-21-designated-entity-cancellation-notice.md` | 5 | per-policy KB injection (universal block), slot 6/6; ALSO loaded by cross_policy.load_universal_kb_block() |

## ORPHANED (KB root) — 1 files (38 KB)

| File | Size (KB) | Why |
|---|---:|---|
| `KB-AUDIT.md` | 38 | KB root files are not part of any load path |

## ORPHANED (bumped from top-N) — 46 files (159,984 KB)

| File | Size (KB) | Why |
|---|---:|---|
| `by-coverage/auto/Symbol 2 8 9 versus 2.pdf` | 229 | in a load folder but didn't sort into the top-N slots |
| `by-coverage/gl/Exclusion L - Your work (faulty work).pdf` | 769 | in a load folder but didn't sort into the top-N slots |
| `by-coverage/gl/Seperation of Insured.pdf` | 57 | in a load folder but didn't sort into the top-N slots |
| `by-coverage/gl/The Perfect AI form.pdf` | 4226 | in a load folder but didn't sort into the top-N slots |
| `by-coverage/property/Property Cheat Sheet.pdf` | 113 | in a load folder but didn't sort into the top-N slots |
| `by-coverage/umbrella-excess/Umbrella Form.pdf` | 1927 | in a load folder but didn't sort into the top-N slots |
| `contracts/Handout Material.pdf` | 471 | in a load folder but didn't sort into the top-N slots |
| `contracts/MSAs.pdf` | 14380 | in a load folder but didn't sort into the top-N slots |
| `contracts/top 10 scariest insurance policy terms.pdf` | 244 | in a load folder but didn't sort into the top-N slots |
| `methodology/04_winning-the-account.md` | 2 | in a load folder but didn't sort into the top-N slots |
| `methodology/2-Contract Analysis (print-friendly).pdf` | 777 | in a load folder but didn't sort into the top-N slots |
| `methodology/2017_risk_transfer_update.pdf` | 3076 | in a load folder but didn't sort into the top-N slots |
| `methodology/50-State Survey_Late Notice & the Prejudice Requirement (Schenk, Simantob) 2012.pdf` | 509 | in a load folder but didn't sort into the top-N slots |
| `methodology/Book of Solutions.pdf` | 10016 | in a load folder but didn't sort into the top-N slots |
| `methodology/Case Study 1 - Auto Policy.pdf` | 9444 | in a load folder but didn't sort into the top-N slots |
| `methodology/Case Study 1 - Excess Policy.pdf` | 3806 | in a load folder but didn't sort into the top-N slots |
| `methodology/Case Study 1 - General liability.PDF` | 325 | in a load folder but didn't sort into the top-N slots |
| `methodology/Case Study 1 - IM.pdf` | 8671 | in a load folder but didn't sort into the top-N slots |
| `methodology/Case Study 1 - Property.PDF` | 459 | in a load folder but didn't sort into the top-N slots |
| `methodology/Challenger Article.pdf` | 3767 | in a load folder but didn't sort into the top-N slots |
| `methodology/Challnger Sale cheat sheets learn tailor and take control.pdf` | 1185 | in a load folder but didn't sort into the top-N slots |
| `methodology/Decision Email_Qualification example.pdf` | 131 | in a load folder but didn't sort into the top-N slots |
| `methodology/E-book_ 7 Unexpected Ways To Increase Sales.pdf` | 6960 | in a load folder but didn't sort into the top-N slots |
| `methodology/Embedded in JC.pdf` | 64 | in a load folder but didn't sort into the top-N slots |
| `methodology/Five Pillars of Success.pdf` | 755 | in a load folder but didn't sort into the top-N slots |
| `methodology/Forest For the Trees.pdf` | 767 | in a load folder but didn't sort into the top-N slots |
| `methodology/Form Library.pdf` | 17596 | in a load folder but didn't sort into the top-N slots |
| `methodology/Horrible Policy Forms - Handout.pdf` | 5075 | in a load folder but didn't sort into the top-N slots |
| `methodology/KB-LOAD-AUDIT.md` | 30 | in a load folder but didn't sort into the top-N slots |
| `methodology/leased employee ISSUE flowchart.pdf` | 772 | in a load folder but didn't sort into the top-N slots |
| `methodology/Logical Fallacies List.pdf` | 126 | in a load folder but didn't sort into the top-N slots |
| `methodology/Meet the Guy Who Solved Uber's Insurance Problem.boxnote` | 1 | in a load folder but didn't sort into the top-N slots |
| `methodology/OSHA-Recordkeeping-and-Inspections.pdf` | 795 | in a load folder but didn't sort into the top-N slots |
| `methodology/PC - CAUA.pdf` | 3559 | in a load folder but didn't sort into the top-N slots |
| `methodology/PF Tech.pdf` | 10881 | in a load folder but didn't sort into the top-N slots |
| `methodology/PFC-K - Process Flow Chart KEY.pdf` | 40 | in a load folder but didn't sort into the top-N slots |
| `methodology/Professional Fees Coverage.pdf` | 373 | in a load folder but didn't sort into the top-N slots |
| `methodology/Read your contract.pdf` | 232 | in a load folder but didn't sort into the top-N slots |
| `methodology/RMF-CHECKLIST-AUDIT.md` | 6 | in a load folder but didn't sort into the top-N slots |
| `methodology/SBBNW_Willo22121912470.pdf` | 4596 | in a load folder but didn't sort into the top-N slots |
| `methodology/Strategies for Managing the Consequence... and Management in Engineering- (ASCE).pdf` | 897 | in a load folder but didn't sort into the top-N slots |
| `methodology/The Black Swan- The Impact of the Highly Improbable (Hardcover).pdf` | 442 | in a load folder but didn't sort into the top-N slots |
| `methodology/When Workers Aren't Employees _ Expert Commentary _ IRMI.com.pdf` | 602 | in a load folder but didn't sort into the top-N slots |
| `methodology/When Workers Aren't Employees.pdf` | 60 | in a load folder but didn't sort into the top-N slots |
| `methodology/White Paper Examples and Design Tips - Venngage.pdf` | 40481 | in a load folder but didn't sort into the top-N slots |
| `methodology/Workplace-Violence-Risk-Management.pdf` | 290 | in a load folder but didn't sort into the top-N slots |

## ORPHANED (folder not in load paths) — 45 files (182,499 KB)

| File | Size (KB) | Why |
|---|---:|---|
| `presentations/3B Concrete - Executive Summary .pdf` | 7772 | strategic/ and presentations/ are reference-only folders |
| `presentations/Amy Wolf Executive Summary.pub` | 9211 | strategic/ and presentations/ are reference-only folders |
| `presentations/Arthur Wright.pdf` | 1229 | strategic/ and presentations/ are reference-only folders |
| `presentations/Christian City (S. Cornell) - Executive Summary.pdf` | 12473 | strategic/ and presentations/ are reference-only folders |
| `presentations/Crank and Chrome Cycles, Inc. (J. Yeretzian).pdf` | 2000 | strategic/ and presentations/ are reference-only folders |
| `presentations/David Lee Executive Summary.pdf` | 1656 | strategic/ and presentations/ are reference-only folders |
| `presentations/DUS - John Beary.pdf` | 1294 | strategic/ and presentations/ are reference-only folders |
| `presentations/ES - GUINN - BBU.pdf` | 1552 | strategic/ and presentations/ are reference-only folders |
| `presentations/ES FINAL DRAFT (PC 21 - Tyler Caffey).pdf` | 4347 | strategic/ and presentations/ are reference-only folders |
| `presentations/Executive Summary (J. Murray).pdf` | 5917 | strategic/ and presentations/ are reference-only folders |
| `presentations/Executive Summary - Jonathon Post - BBU PC 19.pdf` | 3583 | strategic/ and presentations/ are reference-only folders |
| `presentations/Executive Summary for Baby Haven.pdf` | 5037 | strategic/ and presentations/ are reference-only folders |
| `presentations/Executive Summary- Dameron- Mona Lisa- Final.pdf` | 2541 | strategic/ and presentations/ are reference-only folders |
| `presentations/FINAL EXEC SUMMARY (PC 21 - Stephen Barbari).pdf` | 3288 | strategic/ and presentations/ are reference-only folders |
| `presentations/Madman EXECUTIVE SUMMARY.pdf` | 3433 | strategic/ and presentations/ are reference-only folders |
| `presentations/Madman Motors (T. Barone, J. Mongold) - Executive Summary.pdf` | 3433 | strategic/ and presentations/ are reference-only folders |
| `presentations/Nuance (L. Lewis) - Executive Summary.pdf` | 1951 | strategic/ and presentations/ are reference-only folders |
| `presentations/Presstige Executive Summary (PC 21 - Russell Rands).pdf` | 9545 | strategic/ and presentations/ are reference-only folders |
| `presentations/SKE.ExecSumm.PlusPower (1).pdf` | 15916 | strategic/ and presentations/ are reference-only folders |
| `presentations/Step 6 Exec Summary - JC.pdf` | 6076 | strategic/ and presentations/ are reference-only folders |
| `presentations/Step 6 Exec Summary Arthur Wright.pdf` | 5323 | strategic/ and presentations/ are reference-only folders |
| `presentations/Step 6 Exec Summary Printable.pdf` | 2899 | strategic/ and presentations/ are reference-only folders |
| `presentations/Step 6 Executive Summary.pdf` | 3957 | strategic/ and presentations/ are reference-only folders |
| `presentations/Step 6- Executive Summary_Emily Reiter.pdf` | 11367 | strategic/ and presentations/ are reference-only folders |
| `strategic/02 Captive Definitions & Acronyms.pdf` | 214 | strategic/ and presentations/ are reference-only folders |
| `strategic/03_strategic-questions.md` | 2 | strategic/ and presentations/ are reference-only folders |
| `strategic/2023 Captive Presentation Steps.pdf` | 451 | strategic/ and presentations/ are reference-only folders |
| `strategic/2023 Captive STD Shows.pdf` | 5364 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captive 101 slides for Brown & Brown.pdf` | 1846 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captive Matrix.pdf` | 360 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captive-Case-Studies-and-Data.pdf` | 2318 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captive-Case-Studies-Duval-Precast.pdf` | 693 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captive-Definitions-and-Acronyms.pdf` | 202 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captive-Equity-Statements-Deep-Dive.pdf` | 473 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captive-Feasibility-Study-Process.pdf` | 355 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captive-IRS-Tax-Admin-Documents.pdf` | 1123 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captive-Premium-Structure-and-Training-201.pdf` | 1540 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captive-Program-Cost-Breakouts.pdf` | 706 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captive-Standard-Coverage-Template-SCT.pdf` | 672 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captive-Table-Presentation-Sales-Script.pdf` | 792 | strategic/ and presentations/ are reference-only folders |
| `strategic/Captives Binder.pdf` | 12338 | strategic/ and presentations/ are reference-only folders |
| `strategic/Charter-Partners-Community-Captive.pdf` | 604 | strategic/ and presentations/ are reference-only folders |
| `strategic/CRI-Corporate-Overview.pdf` | 558 | strategic/ and presentations/ are reference-only folders |
| `strategic/Finwall Binder.pdf` | 25969 | strategic/ and presentations/ are reference-only folders |
| `strategic/Typical Aggregate Group Captive Structure.pdf` | 118 | strategic/ and presentations/ are reference-only folders |

## ORPHANED (in subfolder, loader doesn't recurse) — 9 files (49,328 KB)

| File | Size (KB) | Why |
|---|---:|---|
| `by-coverage/gl/archive/6_ CGL endorsements and miscellaneous coverage forms. - Free Online Library.pdf` | 829 | subdir of a load-folder; pipeline globs only top-level *.md/*.pdf |
| `by-coverage/gl/archive/Additional insured endorsement overview.pdf` | 1052 | subdir of a load-folder; pipeline globs only top-level *.md/*.pdf |
| `by-coverage/gl/archive/Additional insured evoloution.pdf` | 75 | subdir of a load-folder; pipeline globs only top-level *.md/*.pdf |
| `by-coverage/gl/archive/Additionl insured and contractual indemnity.pdf` | 138 | subdir of a load-folder; pipeline globs only top-level *.md/*.pdf |
| `by-coverage/gl/archive/Vendors Endorsement - Extend coverage to your vendors.pdf` | 125 | subdir of a load-folder; pipeline globs only top-level *.md/*.pdf |
| `by-coverage/property/archive/annotated property policy.pdf` | 23200 | subdir of a load-folder; pipeline globs only top-level *.md/*.pdf |
| `by-coverage/umbrella-excess/archive/Umbrella 17-18 - bob's comments included.pdf` | 2591 | subdir of a load-folder; pipeline globs only top-level *.md/*.pdf |
| `by-coverage/workers-comp/archive/FL-WC-Statute-Chapter-440.pdf` | 948 | subdir of a load-folder; pipeline globs only top-level *.md/*.pdf |
| `by-coverage/workers-comp/archive/WC-Experience-Rating-Complete-Guide.pdf` | 20370 | subdir of a load-folder; pipeline globs only top-level *.md/*.pdf |

## ORPHANED (non-loadable extension) — 78 files (436,079 KB)

| File | Size (KB) | Why |
|---|---:|---|
| `by-coverage/auto/Individual owned cars on a auto policy for the auto seciton.doc` | 50 | loader only reads .md and .pdf; .doc files are skipped |
| `by-coverage/auto/MCS90.docx` | 24 | loader only reads .md and .pdf; .docx files are skipped |
| `by-coverage/pollution/CGL POLLUTION EXCLUSION MATRIX.docx` | 174 | loader only reads .md and .pdf; .docx files are skipped |
| `by-coverage/umbrella-excess/Drop Down provisions Umbrella draft 1.docx` | 152 | loader only reads .md and .pdf; .docx files are skipped |
| `contracts/Contractual Risk Transference Outline and Detailed Notes.docx` | 23 | loader only reads .md and .pdf; .docx files are skipped |
| `contracts/Contractual Risk Transference.pptx` | 33529 | loader only reads .md and .pdf; .pptx files are skipped |
| `methodology/2-Contract (aka Project) Analysis.xlsx` | 568 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/2-Contract Analysis . Sheridan Fruit .Rfaherty . V2  11.14.23.xlsx` | 17852 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/3-Seeking to Understand AKA, Strategic Questions.xlsx` | 97 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/3-Seeking to Understand.xlsx` | 89 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/5-LED Example.xlsx` | 23 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/6-Abbreviated Exec Summary.xlsx` | 514 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/8A-Winning the Account.docx` | 440 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/8B-Connecting with Your Customer.docx` | 438 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/8C-Creating the Final Strategy.docx` | 439 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/8D-Final Meeting Outline.docx` | 1209 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/8E-Qualification Criteria.xlsx` | 162 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/A Look at Fiduciary Liability.docx` | 136 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/Affinium Call Script.docx` | 18 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/Affinium Conference Call Transcript.docx` | 20 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/Affinium Contract Analysis.xlsx` | 582 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/Affinium Security Executive Summary 10.18.23.pptx` | 7990 | loader only reads .md and .pdf; .pptx files are skipped |
| `methodology/Affinium Security Executive Summary.pptx` | 8639 | loader only reads .md and .pdf; .pptx files are skipped |
| `methodology/BB Retail Detailed Template.pptx` | 12346 | loader only reads .md and .pdf; .pptx files are skipped |
| `methodology/BBU Qualification - Affinium.xlsx` | 162 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/BBU Qualification form.xlsx` | 163 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/Conference Call - Towncenter Transcript.docx` | 39 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/Conference Call - Transcript from Eric Starke.docx` | 34 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/Diary Process - FSCC.pptx` | 1255 | loader only reads .md and .pdf; .pptx files are skipped |
| `methodology/Example - Step 1 - Qualification (Baker).xlsx` | 75 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/Final Project (READ ME FIRST).docx` | 40 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/Flatbread Contract Analysis.xlsx` | 566 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/LDE Affinium.xlsx` | 22 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/LDE Example.xls.xlsx` | 25 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/LDE Example.xlsx` | 22 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/Master Coverage Form Request.docx` | 67 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/Misc Unacceptable Endorsements as of 07.21.20.xlsx` | 32 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/Objections AMG Playbook.docx` | 41 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/PFC-D - Process Flow Chart Diary.xlsx` | 22 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/phoenix Process Flow Chart Diary.xlsx` | 20 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/Process Flow Chart Diary - Affinium Security.xlsx` | 20 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/Process Flow Chart Diary - Pool Works - Jared.xlsx` | 20 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/Progress Report.doc` | 210 | loader only reads .md and .pdf; .doc files are skipped |
| `methodology/Sample Final Meeting Outline (Steen Enterprises).docx` | 1209 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/Step 2 - completed CGL Pleasant Places.xlsx` | 501 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/Step 8 - Winning the Account- Affinium Security.docx` | 444 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/Step 8 - Winning the Account- Sanibel Island Golf Course.docx` | 444 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/Template Contract Analysis.xlsx` | 564 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/Template_Contract_Analysis.xlsx` | 564 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/Things to consider EPLI PEO.docx` | 30 | loader only reads .md and .pdf; .docx files are skipped |
| `methodology/Transcend Policy Analysis.xlsx` | 580 | loader only reads .md and .pdf; .xlsx files are skipped |
| `methodology/Will Quiala - Executive Summary.pptx` | 9302 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/ASI Lumber Executive Summary 1.pptx` | 8120 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/CVK Electric - Executive Summary (S. Poulin).docx` | 1770 | loader only reads .md and .pdf; .docx files are skipped |
| `presentations/ES PF Techfinal.pptx` | 47746 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/Executive Summary - Mainline Private Security.pptx` | 6220 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/Executive Summary for Baby Haven.docx` | 23844 | loader only reads .md and .pdf; .docx files are skipped |
| `presentations/Executive Summary- Jonathan's Bay Assoc.pptx` | 8378 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/Executive Summary.pptx` | 93095 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/Executive Summary_Paul Davis of NW GA-FINAL (1).pptx` | 32353 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/Final Project - Executive Summary - Space Coast.pptx` | 17803 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/Four Seasons Concrete Construction LLC Exec Summary - Wickens.pptx` | 3580 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/Huron Sprinkers (P. Nicholson) - Executive Summary.docx` | 956 | loader only reads .md and .pdf; .docx files are skipped |
| `presentations/Huron Sprinklers (P. Nicholson) - Executive Summary.docx` | 956 | loader only reads .md and .pdf; .docx files are skipped |
| `presentations/Indian Hills - Tyler Brandeburg.pptx` | 11100 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/Mid State Middle Mason Zandi.pptx` | 5412 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/Nuance (B. Cescutti) - Executive Summary.doc` | 13480 | loader only reads .md and .pdf; .doc files are skipped |
| `presentations/Nuance (D. Branning) - Executive Summary.doc` | 1322 | loader only reads .md and .pdf; .doc files are skipped |
| `presentations/Seaside Condo Association.docx` | 15893 | loader only reads .md and .pdf; .docx files are skipped |
| `presentations/Sunbelt Metals - Reid Summers.pptx` | 13280 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/Sweetwater (L. Shannon) - Executive Summary.docx` | 3972 | loader only reads .md and .pdf; .docx files are skipped |
| `presentations/Total Fitness Equipment - Executive Summary.docx` | 5784 | loader only reads .md and .pdf; .docx files are skipped |
| `presentations/United Methodist City Society (A. Mantis) .pptx` | 3825 | loader only reads .md and .pdf; .pptx files are skipped |
| `presentations/Wes Carter Executive Summary.docx` | 3298 | loader only reads .md and .pdf; .docx files are skipped |
| `presentations/White Chapel Church of God.docx` | 10218 | loader only reads .md and .pdf; .docx files are skipped |
| `strategic/FS & Surety.docx` | 26 | loader only reads .md and .pdf; .docx files are skipped |
| `strategic/Sample Final Meeting Outline (Steen Enterprises).docx` | 1209 | loader only reads .md and .pdf; .docx files are skipped |
| `strategic/Step 8 - Winning the Account- Sanibel Island Golf Course.docx` | 455 | loader only reads .md and .pdf; .docx files are skipped |


## Per-folder summary

| Folder | Total files | Loaded | Orphaned (bumped) | Orphaned (subdir) | Orphaned (other) |
|---|---:|---:|---:|---:|---:|
| `(root)/` | 1 | 0 | 0 | 0 | 1 |
| `by-coverage/auto/` | 9 | 6 | 1 | 0 | 2 |
| `by-coverage/cyber/` | 2 | 2 | 0 | 0 | 0 |
| `by-coverage/do-epli/` | 2 | 2 | 0 | 0 | 0 |
| `by-coverage/gl/` | 14 | 6 | 3 | 5 | 0 |
| `by-coverage/inland-marine/` | 2 | 2 | 0 | 0 | 0 |
| `by-coverage/pollution/` | 3 | 2 | 0 | 0 | 1 |
| `by-coverage/professional-liability/` | 1 | 1 | 0 | 0 | 0 |
| `by-coverage/property/` | 8 | 6 | 1 | 1 | 0 |
| `by-coverage/umbrella-excess/` | 9 | 6 | 1 | 1 | 1 |
| `by-coverage/workers-comp/` | 6 | 4 | 0 | 2 | 0 |
| `contracts/` | 7 | 2 | 3 | 0 | 2 |
| `methodology/` | 87 | 4 | 37 | 0 | 46 |
| `presentations/` | 47 | 0 | 0 | 0 | 47 |
| `strategic/` | 24 | 0 | 0 | 0 | 24 |
| `universal/` | 6 | 6 | 0 | 0 | 0 |
