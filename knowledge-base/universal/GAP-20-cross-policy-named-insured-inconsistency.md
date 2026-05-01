# Cross-Policy Named Insured Inconsistency Across Program

## Purpose
Detect mismatches in the Named Insured / Additional Named Insured schedules **across all policies in the same program**. Flag entities that appear on one policy but not another where they should appear, and produce a cross-policy entity matrix that surfaces coverage holes at primary, excess, and umbrella attachment points.

## Why it matters
This is the dominant pattern of program-coordination defect. The pattern can run in either direction:
- **Primary covers more entities than Umbrella:** Lower-tier primary policies (especially Auto) sometimes name 6+ Runbeck-family entities, while the Umbrella names only 3. Any auto liability claim involving an entity not on the Umbrella schedule has a **hard cap at the primary limit** with no excess attachment.
- **Umbrella covers entities the primary doesn't:** Even more dangerous — the Umbrella can't drop down to cover an entity that has no primary policy because there's no underlying for the Umbrella to follow.
- **Different entity-name format on each policy:** "Runbeck Election Services Inc" on one policy, "Runbeck Election Services LLC" on another — the same human-readable entity, but two different legal persons in claim litigation.

GAP-01 (Named Insured Verification) detects mismatches between the Dec and the client's true legal entity. GAP-20 detects mismatches **across multiple policies in the same program**, which is a different and orthogonal class of defect.

## Detection rules

### Rule 1 — Build a cross-policy entity matrix
For every program audited, construct a table:

| Entity (canonical legal name) | CGL | Auto | WC | Umbrella | Cyber | Tech E&O | Crime | Property |
|---|---|---|---|---|---|---|---|---|
| Runbeck Election Services LLC | ✗ Inc | ✗ Inc | ✗ Inc | ✗ Inc | ✓ LLC | ✗ Inc | ... | ... |
| Runbeck Investments LLC | ✓ | ✓ | — | ✓ | ✓ | — | ... | ... |
| Runbeck Properties LLC | ✗ | ✓ | — | ✓ | ✓ | — | ... | ... |
| Runbeck Graphics Inc | ✓ | ✓ | — | ✓ | ✓ | — | ... | ... |
| Runbeck Companies 401(k) Profit Sharing Plan | — | ✓ | — | ✗ | ✗ | — | ... | ... |
| Lincoln Shields LLC | — | ✓ | — | ✗ | ✗ | — | ... | ... |
| Black Mountain Investment Co LLC | — | ✓ | — | ✗ | ✗ | — | ... | ... |

Legend: ✓ = present and correctly named, ✗ = present but with name error, — = not on this policy.

### Rule 2 — Flag every cell that creates a coverage hole
Each missing or mismatched cell is a finding:
- **Entity on primary but not on umbrella** → primary-limit hard cap
- **Entity on umbrella but not on primary** → umbrella has nothing to follow form to (no coverage)
- **Entity on some primaries but not others** → coverage exists for some claim types but not others (e.g., on Auto but not GL means a slip-and-fall at a Lincoln Shields location is uncovered)
- **Entity name format differs across policies** → potential litigation issue identifying the insured

### Rule 3 — Flag entity-type mismatches against legal reality
If the client's legal entity is "Runbeck Election Services, LLC" but the policy Dec says "Runbeck Election Services Inc" with Form of Business = Corporation, this is a GAP-01 finding **and** a GAP-20 finding when it persists across multiple policies in the same program (indicates systemic broker oversight, not a single typo).

### Rule 4 — Flag Broad Form NI dependencies
Many policies include a Broad Form Named Insured endorsement that automatically extends coverage to subsidiaries acquired during the policy term **except** specific entity types (commonly LLCs). When the client has LLC subsidiaries, the Broad Form NI does NOT cure the missing-entity problem. Flag any Broad Form NI extension that excludes the actual entity type of the client's missing entities.

## Severity scoring
- **Critical (Ugly / 20–25):** Entity is on primary but missing from umbrella, AND that entity has material operations, real property, employees, or revenue exposure
- **Critical (Ugly / 20–25):** Entity name format inconsistent across 3+ policies in the same program (systemic identification defect)
- **Needs Attention (Bad / 9–19):** Entity missing from a single policy where it should appear, but covered elsewhere in the program
- **Needs Attention (Bad / 9–19):** Broad Form NI extension excludes the entity type of the client's actual subsidiaries (LLC excluded but client has LLC subs)
- **Informational (Good / 1–8):** All entities consistently named across all policies; Broad Form NI matches actual subsidiary types

## Example flagged finding
> Cross-policy entity audit on Runbeck program:
> - **Lincoln Shields LLC** appears on the Hanover Auto policy (461-0174 Additional Named Insured Endorsement) but does NOT appear on the Hanover Umbrella (475-0174). Any auto liability claim involving Lincoln Shields exceeding the $1M Auto CSL has no Umbrella excess. Risk score 22/25.
> - **Black Mountain Investment Co LLC** has the same defect — present on Auto, absent from Umbrella. Risk score 22/25.
> - **Runbeck Properties LLC** appears on the Umbrella (475-0174) and on the Cyber (Policy Change #1) but does NOT appear on the Commercial Package CGL. A premises liability claim at a Runbeck Properties location has no GL coverage. Risk score 25/25 (most severe — the Umbrella has nothing to drop down to).
> - **Inc vs LLC entity-type mismatch** is present on 6 of 7 verified policies (all except Cyber). Cyber Policy Change #1 dated 4/1/2025 corrected the name to "Runbeck Election Services LLC" but the same correction was not made on the other 6 program policies. This is a systemic defect indicating the Cyber correction was a localized fix, not a program-wide cleanup. Risk score 24/25.

## Related KB files
- GAP-01 named-insured-verification.md (single-policy entity match)
- GAP-08 umbrella-structure.md (umbrella attachment patterns)
