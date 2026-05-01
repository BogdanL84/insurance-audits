# Contract-Specific Coverage Satisfaction Rules

## Purpose
Verify that policy limits satisfy customer contract requirements on a **per-coverage-line** basis, accounting for whether each contract permits Umbrella attachment to satisfy primary minimums or requires standalone primary limits.

## Why it matters
Many customer contracts (especially county/state government and large enterprise vendors) write minimum-limit requirements differently for each coverage line. A typical pattern: the contract permits the General Liability minimum to be satisfied via "primary plus umbrella," but the Auto Liability minimum **must be standalone primary** with no umbrella attachment. Comparing total program limits to the contract requirement misses this — a $1M Auto + $10M Umbrella does NOT satisfy a "$2M Auto CSL" requirement when the contract bars umbrella attachment for Auto.

This is a direct, current, uncured contract breach the moment the policy incepts. It exposes the insured to:
- Vendor termination for cause
- Liquidated damages clauses
- Indemnification obligations to the customer
- Disqualification from future RFPs

## Detection rules

### Rule 1 — Parse contract requirements per coverage line
For each customer contract:
1. Extract minimum-limit requirements separately for: General Liability, Auto Liability, Workers Comp, Cyber, Tech E&O, Professional Liability, Property, Umbrella, Crime
2. For each line, identify whether the contract permits umbrella attachment to satisfy the primary requirement, or requires standalone primary limits
3. Common contract language patterns:
   - **Permits umbrella:** "General Liability of $2,000,000 per occurrence, which may be satisfied by primary and umbrella combined"
   - **Requires standalone:** "Auto Liability of $2,000,000 combined single limit" (no umbrella mention) — by default, umbrella is NOT presumed to satisfy
   - **Express bar:** "Workers Compensation as required by statute, with Employer's Liability of $1,000,000 per accident — must be primary coverage"

### Rule 2 — Compare per-coverage-line policy limits against per-coverage-line contract requirements
For each line:
1. Identify policy primary limit (from the Dec page)
2. Identify whether umbrella follows form to that line (from Umbrella Schedule of Underlying Policies)
3. Compare to contract requirement under that contract's specific attachment rule

### Rule 3 — Flag every coverage line that fails standalone-primary requirements
A finding is generated when:
- The contract requires standalone primary limits AND the primary limit is below the requirement, OR
- The contract permits umbrella but the underlying schedule does NOT list this line (umbrella won't follow form), OR
- The contract requires statute-minimum standalone (e.g., WC) AND a non-statutory carve-out exists

### Rule 4 — Apply industry default presumption when contract is silent
When the contract is silent on whether umbrella may satisfy:
- **Auto Liability:** default = standalone primary required (most common in govt/enterprise contracts)
- **Workers Comp:** default = standalone primary required (statutory in every state)
- **Tech E&O / Professional Liability:** default = standalone primary required
- **General Liability:** default = umbrella permitted unless contract says otherwise
- **Cyber:** default = standalone primary required (rarely covered by umbrella anyway)

## Severity scoring
- **Critical (Ugly / 20–25):** Coverage line below contract minimum AND contract bars or is silent on umbrella attachment AND policy is currently active = uncured breach
- **Critical (Ugly / 20–25):** Statutory coverage (WC, Auto in compulsory states) below contract minimum
- **Needs Attention (Bad / 9–19):** Coverage line below contract minimum BUT umbrella permitted AND umbrella schedule includes the line
- **Informational (Good / 1–8):** All coverage lines meet or exceed contract minimums on a standalone-primary basis

## Example flagged finding
> Maricopa County contract Section IV.A. requires Commercial Auto Liability of $2,000,000 Combined Single Limit. The contract permits umbrella attachment to satisfy General Liability minimums (Section IV.B) but does NOT include similar language for Auto Liability. Runbeck's Hanover Auto policy AW4-H221414-05 carries $1,000,000 CSL primary. Even with the $10,000,000 Hanover Umbrella sitting above, the Auto requirement is unsatisfied because the contract's language structure permits umbrella for GL only. **Risk score 25/25 — uncured contract breach as of policy inception 4/1/2025.**

## Related KB files
- GAP-08 umbrella-structure.md (umbrella attachment patterns)
- GAP-21 designated-entity-cancellation-notice.md (Auto-specific)
