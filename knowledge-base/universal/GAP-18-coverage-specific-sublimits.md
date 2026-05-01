# Coverage-Specific Sublimits for Business-Relevant Cargo and Equipment

## Purpose
Identify policy sublimits that are technically present but materially inadequate given the insured's actual business operations. Focus on electronic equipment, cargo-in-transit, specialty tools, and other line items where industry-standard sublimits dramatically underprice the insured's real exposure.

## Why it matters
Sublimits are easy to miss because they appear deep inside broadening endorsements rather than on the Dec page. A $500 electronic equipment sublimit is invisible to a Dec-page-only review, but for a company that ships thousands of dollars of laptops, scanners, or specialized hardware in a single covered auto, that sublimit can render the coverage practically worthless. The same pattern recurs in:
- Hired Auto Physical Damage caps (often $50K, inadequate for box trucks)
- Cargo Pollution Liability (often excluded entirely or sub-limited)
- Loss of Use / Rental Reimbursement (often $50/day)
- Sound/Visual Equipment (often $500–$1,500)
- Bailee Property (often $5,000)

## Detection rules

### Rule 1 — Inventory all sublimits across the policy
Scan every endorsement (not just the Dec) for dollar caps that are:
- Lower than the policy's main limit
- Specific to a category of property, expense, or coverage extension
- Often denoted by phrases like "the most we will pay," "subject to a limit of," "aggregate limit," "per accident limit," "per item limit"

Common locations:
- Business Auto: 461-0155 Broadening Endorsement (Hanover) §§7, 9, 11, 12, 14, 15
- Commercial Property: BPP, EDP Floater, Inland Marine schedules
- Cyber: Coverage Schedule (per coverage column)
- Crime: Coverage Schedule

### Rule 2 — Compare each sublimit to the insured's operational profile
For each sublimit, determine whether the insured's business creates exposure that materially exceeds the cap:

| Sublimit category | Industry std | Flag when insured is... |
|---|---|---|
| Electronic equipment (auto) | $500–$1,500 | A tech company, hardware shipper, IT services, election services, medical device |
| Hired Auto Physical Damage | $25K–$50K | Anyone renting box trucks, cargo vans, specialty vehicles |
| Cargo / Property in Transit | $5K–$25K | Manufacturer, distributor, services with valuable hardware delivery |
| Loss of Use / Rental | $30/day–$50/day | Service business dependent on vehicle uptime |
| Cyber Deception (social engineering) | $100K–$250K limit / equal retention | Any business with wire transfers >$100K |
| Cyber Proof of Loss | $100K–$250K | Any business that would need forensic accounting to prove a loss |
| Crime — Funds Transfer Fraud | $100K–$500K | Any business with payable processes >$50K |

### Rule 3 — Calculate effective recoverable
For sublimits where the retention equals the limit (common in Cyber), the effective recoverable = $0. Flag this as a critical finding regardless of stated business profile — a coverage with $0 mathematical recovery is a phantom coverage.

### Rule 4 — Cross-reference sublimit erosion against main aggregate
Flag when a sublimit is **also subject to the main policy aggregate**, meaning it not only caps the recovery for that line but also erodes the aggregate available for other coverages. Cyber policies routinely structure sublimits this way.

## Severity scoring
- **Critical (Ugly / 20–25):** Effective recoverable is $0 (retention = limit), OR sublimit is < 5% of insured's operational exposure on that category, OR sublimit erodes a contract-required aggregate
- **Needs Attention (Bad / 9–19):** Sublimit is 5–25% of operational exposure
- **Informational (Good / 1–8):** Sublimit is 25%+ of operational exposure or industry-standard for the business profile

## Example flagged finding
> Hanover Business Auto AW4-H221414-05 includes Audio, Visual and Data Electronic Equipment Coverage via Broadening Endorsement 461-0155 §11. The sublimit is **$500 per loss** with no separate deductible. Runbeck Election Services regularly transports election hardware (ballot scanners, ballot-on-demand printers, server equipment) in covered vehicles, with single-load values commonly exceeding $25,000. The $500 sublimit covers **less than 2%** of typical transport exposure. Recommend separate Inland Marine Contractors Equipment policy or EDP Floater. **Risk score 22/25.**

> AmTrust Cyber AES1231913 02 Cyber Deception sublimit is **$250,000 limit / $250,000 retention**. Effective recoverable on any single loss = $0. Loss of $300K recovers $50K. Loss of $500K recovers $250K (less than 50% of the loss). **Risk score 25/25 — phantom coverage.**

## Related KB files
- GAP-17 contract-specific-coverage-satisfaction.md
