# Umbrella Structure (EXPANDED)

## Purpose
Verify that the Commercial Umbrella properly attaches over all primary coverages, that all entities on primary policies also appear on the Umbrella, and that the Umbrella's exclusion structure does not silently strip coverage from lines the underlying primary covered.

## What's new in this expanded version
This file previously focused on Umbrella exclusion patterns and follow-form scope. It now also covers:
1. **Entity attachment gap at primary-to-Umbrella boundary** — entities on primary but absent from Umbrella have a hard cap at the primary limit (cross-reference GAP-20)
2. **Schedule of Underlying Policies blank-line analysis** — blank lines indicate no excess coverage exists for that line, which is a finding of its own
3. **Horizontal exhaustion patterns** beyond just the standard "Other Insurance" clause
4. **Stacked exclusions across Coverage A (follow form) and Coverage B (umbrella)** that strip professional/cyber liability even when underlying covers it

## Why it matters
The Umbrella is supposed to be the "catch-all" excess layer, but in practice it often has structural gaps that the client doesn't see:
- Entities named on Auto/CGL drop out at the Umbrella attachment point
- The Schedule of Underlying Policies has blank lines for coverages the client thinks are excessed (Tech E&O, D&O, Cyber)
- Coverage B (umbrella) carries direct exclusions that don't exist on Coverage A (follow form), creating an exclusion expansion at the upper layer
- "Maintenance of Underlying" clauses can void the Umbrella entirely if any underlying lapses

## Detection rules

### Rule 1 — Build the Schedule of Underlying Policies as a structured table
For every line in the Schedule (commonly 8–12 lines):
- Coverage line name (a. CGL, b. Auto, c. Employer's Liability, d. Liquor, e. Cyber, f. Professional Liability, g. D&O, etc.)
- Underlying carrier
- Underlying policy number
- Underlying limits
- Whether the line is **blank** (no underlying = no follow-form excess for that coverage)

Blank lines are a finding. They mean the Umbrella does not attach over that coverage, even if the insured has a standalone policy for it.

### Rule 2 — Cross-reference Schedule of Underlying Policies against client's actual standalone policies
If the client carries a standalone Cyber, Tech E&O, or D&O policy but the Umbrella's Schedule of Underlying Policies for that line is blank, the standalone has NO umbrella excess. Flag this as a critical structural defect.

### Rule 3 — Build the entity matrix against Umbrella
Compare the Umbrella's Multiple Named Insured endorsement (e.g., Hanover 475-0174) entity list against every primary policy's Named Insured + Additional Named Insured schedule. Flag any entity present on a primary but absent from the Umbrella. Cross-reference GAP-20 for the full cross-policy entity matrix.

### Rule 4 — Identify Coverage B direct exclusions that exceed Coverage A
The Umbrella typically has two coverages:
- **Coverage A** = Follow Form Excess Liability (excesses the underlying)
- **Coverage B** = Umbrella Liability (direct umbrella over the underlying)

Coverage B often has its own list of exclusions in the policy form itself (e.g., Hanover 475-0001 Section VII Exclusions). Some Coverage B exclusions may be **broader** than the underlying primary's exclusions — meaning Coverage B does NOT drop down to fill a gap if Coverage A doesn't follow. Common examples:
- Coverage B excludes professional services entirely even though some underlying GL covers limited professional acts
- Coverage B excludes cyber/privacy entirely even though some underlying covers limited cyber
- Coverage B excludes pollution entirely even though some underlying covers sudden/accidental

### Rule 5 — Identify stacked exclusion endorsements
The Umbrella may attach exclusion endorsements that apply to BOTH Coverage A and Coverage B (e.g., Hanover 475-0027 Total Pollution, 475-0654 Cyber Access/Disclosure, 475-0655 Data Privacy Violation, 475-0661 Cyber Incident, 475-0031 Professional Liability). These compound the structural gaps and effectively zero out coverage on lines that the underlying may purport to cover.

### Rule 6 — Maintenance of Underlying clause
Identify the Maintenance of Underlying clause (commonly Section VIII or IX). This typically requires the insured to maintain underlying primary coverage in full force during the Umbrella term. If any underlying lapses or is reduced below scheduled limits, the Umbrella does NOT drop down to fill the gap — instead, it operates as if the underlying had been at the scheduled limit. This is a hidden trap when the insured allows a standalone Cyber or Tech E&O to lapse.

### Rule 7 — Horizontal Exhaustion clause
Identify whether the Umbrella's Other Insurance clause requires horizontal exhaustion of all underlying primary policies before the Umbrella attaches. Horizontal exhaustion can be expensive in multi-defendant scenarios. Cross-reference any Horizontal Exhaustion finding to the AI Primary/Non-Contributory carve-outs in primary policy AI endorsements (which can stack the same problem at multiple layers).

## Severity scoring
- **Critical (Ugly / 20–25):** Schedule of Underlying Policies has a blank line for a coverage the insured has a standalone for (Cyber, Tech E&O, D&O), AND the insured has material exposure on that line
- **Critical (Ugly / 20–25):** Entity present on a primary but absent from the Umbrella's Multiple Named Insured endorsement, AND the entity has material operations
- **Critical (Ugly / 20–25):** Coverage B carries a direct exclusion that strips coverage Coverage A would otherwise excess (e.g., Coverage B excludes all professional services even though Coverage A could follow form to a limited E&O underlying)
- **Needs Attention (Bad / 9–19):** Multiple stacked exclusion endorsements (3+) compounding to strip a coverage line
- **Needs Attention (Bad / 9–19):** Maintenance of Underlying clause creates a high lapse trap
- **Informational (Good / 1–8):** All underlying lines populated, all primary entities also on Umbrella, no exclusion expansion at Coverage B

## Example flagged finding
> Hanover Commercial Umbrella UH4-H221416-05 Schedule of Underlying Policies has lines f (Professional Liability) and g (D&O) **blank**. Combined with Form 475-0031 (Professional Liability Exclusion Coverage A) and Coverage B Section VII.3.k direct exclusion of professional services, the Umbrella provides **no excess at all** over the standalone WR Berkley E&O policy or any future Tech E&O coverage Runbeck adds. Risk score 25/25 — there is no umbrella over the technology liability tower for an election technology company.
>
> Cross-policy entity attachment audit: Lincoln Shields LLC and Black Mountain Investment Co. LLC appear on the Hanover Auto via 461-0174 but are NOT listed in the Umbrella's Multiple Named Insured endorsement 475-0174. Any auto liability claim involving these entities exceeding the $1M Auto CSL has no Umbrella excess — hard cap at $1M. Risk score 22/25.

## Related KB files
- GAP-20 cross-policy-named-insured-inconsistency.md (cross-policy entity matrix)
