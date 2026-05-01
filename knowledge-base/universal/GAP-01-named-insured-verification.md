# Named Insured Verification (EXPANDED)

## Purpose
Verify that the Named Insured field on the Dec page exactly matches the client's confirmed legal entity name **and entity type** (LLC vs Inc vs Corporation vs Partnership vs Trust vs 401(k) Plan), and that any Broad Form Named Insured extension actually covers the entity types that exist in the client's corporate family.

## What's new in this expanded version
This file previously covered only the basic Dec-page-vs-client-legal-name check. It now also covers:
1. **Entity type validation** — Inc vs LLC vs Corporation vs Partnership vs 401(k) Plan, each requiring different policy treatment
2. **Reverse-check pattern** — when one policy has MORE entities than another in the same program, that's a defect too (handled in detail by GAP-20)
3. **Broad Form NI dependency** — many Broad Form NI extensions explicitly exclude LLCs from automatic coverage of newly acquired/formed subsidiaries; flag this when the client has LLC subsidiaries

## Why it matters
Named Insured errors are the single most common defect in commercial program audits. Every other coverage flows from the Named Insured — if the wrong entity is named, contracts may technically be unsigned by an "insured," and claims may be denied for lack of insurable interest.

The entity-type dimension specifically: Auto and Umbrella policies often have Form-of-Business field that must match. A policy listing "Runbeck Election Services Inc" with Form of Business = Corporation creates a documentary mismatch with a legal entity that is actually an LLC. In litigation, this is fixable but creates avoidable friction and possible coverage delay.

## Detection rules

### Rule 1 — Extract the exact text of the Named Insured from every Dec page
Capture verbatim including:
- Full legal name
- Entity-type suffix (Inc, LLC, Corp, Ltd, Co, etc.)
- Form-of-Business field if present
- Mailing address (for cross-policy consistency check)

### Rule 2 — Compare against the client's confirmed legal entity
The client's confirmed legal entity is established once, then used as the standard. Sources:
- Articles of incorporation/organization
- Tax ID documentation
- Corporate registration in the state of formation
- Client's own confirmation during onboarding

### Rule 3 — Verify entity-type alignment specifically
If the client is an LLC, the Dec must say "LLC" and Form of Business should say "Limited Liability Company." If the Dec says "Inc" with Form of Business "Corporation," this is an entity-type defect even if the human-readable name is otherwise correct.

### Rule 4 — Check Broad Form Named Insured extension coverage
If the policy includes a Broad Form NI endorsement (commonly providing automatic coverage for newly acquired or formed entities during the policy term), examine the entity-type carve-outs:
- Many Broad Form NI extensions explicitly exclude LLCs, partnerships, joint ventures
- Some exclude entities below a certain ownership threshold (50%, 75%)
- Some exclude entities formed in non-US jurisdictions

If the client has any LLC entities in its corporate family, flag that the Broad Form NI will NOT extend coverage to them — they must be expressly listed as Additional Named Insureds.

### Rule 5 — Cross-policy consistency
Maintain a single client-entity-map across all program policies. Flag any entity that appears on one policy but not another where it should (e.g., a property-holding LLC should be on the Property policy AND the Umbrella). For deep cross-policy entity matrix work, see GAP-20.

### Rule 6 — Reverse-check pattern: Auto > CGL/Umbrella entity count
When a Commercial Auto policy lists MORE additional named insureds than the Commercial Package or Umbrella, this is itself a defect — entities present on Auto but absent from Umbrella have a hard cap at the primary limit. The "more is wrong too" insight is counterintuitive but real. Cross-reference to GAP-20.

## Severity scoring
- **Critical (Ugly / 20–25):** Name mismatch between policy Named Insured and client's confirmed legal entity, AND Broad Form NI excludes the actual entity type
- **Critical (Ugly / 20–25):** Entity-type mismatch (Inc vs LLC) persisting across 3+ program policies = systemic defect
- **Needs Attention (Bad / 9–19):** Name mismatch but Additional NI schedule covers the operational entity
- **Needs Attention (Bad / 9–19):** Entity present on primary but missing from umbrella (creates hard cap; cross-reference GAP-20)
- **Informational (Good / 1–8):** Name and entity-type correct; Broad Form NI includes all current and future entity types

## Example flagged finding
> Named Insured on Dec reads "RUNBECK ELECTION SERVICES INC" with Form of Business = Corporation across the Hanover Commercial Package, Hanover Commercial Umbrella, Hanover Commercial Auto, Hartford Management Liability, Arch Security Guards, WR Berkley E&O, and Hanover Workers Comp. Client-confirmed legal entity is "Runbeck Election Services, LLC." The AmTrust Cyber policy is the ONLY policy in the program where the Named Insured correctly shows "Runbeck Election Services, LLC" — corrected via Policy Change #1 dated 4/1/2025 — indicating the issue was identified for one policy but not propagated program-wide. Broad Form Named Insured (Hanover form 421-2916 Item 4.b) explicitly excludes LLCs, partnerships, and joint ventures from automatic coverage, so the Broad Form extension does NOT cure the missing-LLC-entity problem on the other 6 policies. Risk score 24/25.

## Related KB files
- GAP-20 cross-policy-named-insured-inconsistency.md (cross-policy entity matrix)
