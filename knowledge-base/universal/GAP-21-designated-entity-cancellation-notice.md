# Designated Entity Cancellation Notice — Per-Policy-Type Coverage

## Purpose
Verify that every coverage line in the program carries a Designated Entity Cancellation Notice endorsement (e.g., ISO IL 12 01, Hanover 401-1235, equivalent) when the insured has customer contracts requiring direct notice to the customer of any insurance cancellation. Most commonly missing on Commercial Auto despite identical contract requirements as the General Liability.

## Why it matters
Customer contracts (especially county/state government, large enterprise, and franchise relationships) commonly require the insured to provide advance written notice to the customer entity if any required insurance is cancelled or non-renewed. The standard mechanism for satisfying this requirement is a **Notice of Cancellation to Designated Entities** endorsement that lists the customer counterparties by name and address.

A common defect: the Commercial Package GL has the Designated Entity NOC endorsement listing all customer counties, but the Commercial Auto policy lacks an equivalent endorsement entirely. The same customer that requires notice on GL almost always requires notice on Auto. The Auto policy then silently fails to deliver the contractually required notice when cancelled — even though the GL does.

## Detection rules

### Rule 1 — Identify the Designated Entity NOC endorsement on each policy
Look for:
- ISO IL 12 01 (Designated Entity Notice of Cancellation Provided By Us)
- Hanover 401-1235 (Notice of Cancellation to Designated Entity(s))
- Carrier-specific equivalents

These endorsements list specific named entities by mailing address with a specified number of days' notice (commonly 30, 60, or 90).

### Rule 2 — Compare the Designated Entity schedule across all policies in the program
For each policy, capture:
- Whether the endorsement is present at all
- The list of designated entities (by name)
- The notice period for each entity

Then build a cross-policy matrix:

| Entity | CGL | Auto | WC | Umbrella | Cyber |
|---|---|---|---|---|---|
| Maricopa County | ✓ 30 | ✗ absent | ✓ 30 | ✓ 30 | ? |
| Los Angeles County | ✓ 60 | ✗ absent | ✓ 60 | ✓ 60 | ? |
| Douglas County, CO | ✓ 30 | ✗ absent | — | ✓ 30 | ? |
| Sacramento County | ✓ 30 | ✗ absent | — | ✓ 30 | ? |

### Rule 3 — Flag every coverage line missing a customer entity that's listed elsewhere
Each missing-but-required entity-policy combination is a finding. The fact that the GL has the entity is presumptive evidence the contract requires it on Auto/Umbrella too.

### Rule 4 — Flag notice periods below contract requirement
Compare each entity's listed notice period to the customer contract. A 30-day notice on a contract that specifies 60-day or 90-day notice is a separate finding, even if the entity is listed.

### Rule 5 — Cross-reference against state amendatory endorsements
State amendatory endorsements may extend the notice period to the Named Insured beyond the IL 00 17 baseline (e.g., Arizona IL 02 58 extending to 45 days). This affects the Named Insured's protection but does NOT affect the Designated Entity schedule, which is governed by its own endorsement. Both must be checked separately.

## Severity scoring
- **Critical (Ugly / 20–25):** Customer entity required on coverage line by contract, completely absent from policy = uncured contract breach
- **Critical (Ugly / 20–25):** Customer entity present but notice period < contract requirement
- **Needs Attention (Bad / 9–19):** Customer entity present on some program policies but not others, where contract scope is unclear
- **Informational (Good / 1–8):** All customer entities present on all required policies with notice period ≥ contract requirement

## Example flagged finding
> Hanover Commercial Package includes Endorsement 401-1235 (Notice of Cancellation to Designated Entity(s)) listing 8 customer counties (Boulder, Coconino, Amazon, El Paso, San Luis Obispo, Colorado, NY State OGS, City of Boulder) with 30-day notice. The corresponding Hanover Commercial Auto policy AW4-H221414-05 does NOT include any equivalent Designated Entity NOC endorsement. The Auto policy can therefore be cancelled without any direct notice to these customer entities, even though the same contracts that require notice on the GL also require notice on the Auto. Risk score 22/25 — uncured contract breach across all 8 customer relationships.

## Related KB files
- GAP-02 cancellation-notice-verification.md (Named Insured notice baseline)
- GAP-17 contract-specific-coverage-satisfaction.md (per-coverage-line contract requirements)
