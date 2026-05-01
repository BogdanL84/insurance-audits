# Cyber Policy Dec Sheet — Trainable Patterns

## Purpose
Teach the tool to extract every material defect and structural feature from a Cyber policy Dec sheet alone, even when the full policy form is not available. Cyber policies are unusually Dec-heavy — most of the structural defects can be detected from the Dec without reading the policy form.

## Why it matters
Cyber Dec sheets contain dense per-coverage tables with limit, sublimit, retention, retroactive date, and endorsement information. The defects most commonly missed by tools (and by hurried human reviewers) are:
- **Sublimit retentions equal to or larger than the sublimit itself** (effective $0 recoverable)
- **Defense Within Limits** language (erodes aggregate by 60–80% on typical cyber claim)
- **Shared aggregate across all sublimits** (one ransomware claim depletes capacity for 12 other coverages)
- **Choice of law forum** (NY, CA, IL choice clauses move arbitration jurisdiction)
- **Continuity/retroactive date** mismatches with prior policy periods (gaps in claims-made coverage)
- **Customer-contract-required limit shortfalls** (Maricopa $5M vs $4M aggregate, etc.)

Many of these defects are detectable from the Dec sheet alone. The tool should treat the Cyber Dec as a high-value training source.

## Detection rules

### Rule 1 — Build the Sublimit-Retention-Aggregate table
For every coverage line shown on the Dec, extract three numbers:

| Coverage | Sublimit | Retention | Effective recoverable on $X loss |
|---|---|---|---|
| Cyber Deception (social engineering) | $250,000 | $250,000 | $0 on loss ≤ retention; max ($X − $250K, $250K limit) on loss > retention |
| Proof of Loss | $250,000 | $50,000 | up to $200K on losses requiring forensic accounting |
| Funds Transfer Fraud | varies | varies | calculate per line |
| Cyber Extortion / Ransom | varies | varies | calculate per line |
| Data Recovery | varies | varies | calculate per line |
| Business Interruption | varies | varies | calculate per line |
| BI from Suppliers | varies | varies | calculate per line |
| Cyber Event Costs | varies | varies | calculate per line |
| Privacy & Network Security | varies | varies | calculate per line |
| Regulatory Fines | varies | varies | calculate per line |
| Payment Card Liability | varies | varies | calculate per line |
| Media Liability | varies | varies | calculate per line |
| Reputation Harm | varies | varies | calculate per line |

A retention equal to or greater than the sublimit on any line = effective $0 recoverable for that coverage. Critical finding.

### Rule 2 — Identify "Defense Within Limits" notation
Cyber policies almost always have Defense Within Limits — defense costs erode the aggregate. Look on the Dec for explicit notation, or check the "Defense" line item. When DWL applies, the effective indemnity available is often 20–40% of the stated aggregate because cyber claims are forensic-heavy.

### Rule 3 — Identify shared-aggregate structure
Cyber policies typically share a single Aggregate across all coverages listed. Confirm whether sublimits are part of the aggregate (most common, most restrictive) or separate from it. When all sublimits share the aggregate, a single $2M ransomware claim leaves only $2M for any other coverage during the policy year — including BI, Privacy, Regulatory Fines, etc.

### Rule 4 — Choice of Law / Forum
Cyber policies often have choice-of-law clauses pointing to NY, CA, IL, or another non-domicile state. This affects:
- Litigation venue
- Recoverable damages categories
- Punitive damages availability
- Statute of limitations

Flag any choice-of-law clause that does not match the insured's state of formation/operations.

### Rule 5 — Retroactive Date / Continuity Date
Cyber is claims-made. The Retroactive Date determines whether a claim arising from a pre-policy event is covered. Two common defects:
- **Retro date later than prior policy expiration:** creates a gap in coverage
- **Retro date matches policy inception:** no prior-acts coverage at all (very restrictive)
- **Retro date set far back (e.g., 5+ years pre-inception):** good, but verify continuous coverage during that period

### Rule 6 — Customer contract minimum-limit comparison
Compare the Cyber aggregate against every customer contract requirement. Common contract patterns require Cyber Liability limits of $5M, $10M, or higher for elections, healthcare, financial services. Flag every contract where the Cyber aggregate falls short.

### Rule 7 — Underlying Schedule alignment with Umbrella
Cross-reference the Cyber aggregate against the Umbrella's Schedule of Underlying Policies. If the Umbrella's line for Cyber is **blank**, there is no excess over the Cyber primary — the aggregate IS the entire tower.

### Rule 8 — Endorsement summary on Dec
Most Cyber Decs list every endorsement attached to the policy by form number. Extract every endorsement number and search the standard library:
- Coverage extensions (good)
- Coverage exclusions (often bad)
- Sublimit modifications (important)
- Retention modifications (important)
- Named Insured changes (verify against entity matrix)

Flag any endorsement that:
- Reduces a sublimit below a customer-contract requirement
- Adds an exclusion not on the original policy form
- Modifies the retroactive date on any line

### Rule 9 — Extract Named Insured entity-type accuracy
Cyber Decs often have correct LLC/Inc designation when other policies in the same program have the wrong one. Flag this asymmetry — the Cyber Dec is evidence the broker/carrier knew the correct entity type and the other policies should have been corrected.

## Severity scoring
- **Critical (Ugly / 20–25):** Effective recoverable is $0 on any sublimit (retention ≥ limit)
- **Critical (Ugly / 20–25):** Aggregate falls below customer contract requirement, AND Umbrella Schedule of Underlying line for Cyber is blank
- **Critical (Ugly / 20–25):** Defense Within Limits + Shared Aggregate + customer contract minimum that exceeds aggregate post-DWL erosion
- **Needs Attention (Bad / 9–19):** Retroactive date creates a gap with prior policy
- **Needs Attention (Bad / 9–19):** Sublimit erosion affects multiple coverage lines that customer contract specifies
- **Informational (Good / 1–8):** Aggregate ≥ all contract minimums; sublimits well-sized; retro date prior to first known loss; Named Insured correctly typed

## Example flagged finding
> AmTrust Cyber Policy AES1231913 02 (Associated Industries Insurance Company), 4/1/2025 – 4/1/2026:
>
> 1. **Aggregate $4,000,000** — Maricopa County contract requires $5,000,000. Direct shortfall of $1M. Risk 22/25.
>
> 2. **Defense Within Limits** — confirmed on Dec. Industry-typical cyber claim spends 60–80% of recovery on forensics, legal, breach counsel, PR. Effective indemnity from a $4M aggregate after DWL erosion ≈ $800K–$1.6M on a single claim. Risk 22/25.
>
> 3. **Cyber Deception sublimit $250,000 / retention $250,000** — effective recoverable = $0. Phantom coverage. Risk 25/25.
>
> 4. **Proof of Loss sublimit $250,000 / retention $50,000** — caps forensic accounting expense at $200K, which may be inadequate for proving up a multi-million dollar BI loss. Risk 18/25.
>
> 5. **Shared aggregate** — All coverages (Ransom, Data Recovery, Bricking, BI, BI from Suppliers, Reputation Harm, Cyber Event, Privacy & Network Security, Regulatory Fines, Payment Card, Media, Proof of Loss, Cyber Deception) share the single $4M aggregate. Single $2M ransomware claim leaves $2M for the rest of the year. Risk 20/25.
>
> 6. **Choice of Law: New York** — insured is Arizona-domiciled. Litigation venue and damage categories controlled by NY law. Risk 14/25.
>
> 7. **Retro Date 4/1/2023** — prior-acts coverage extends 2 years pre-inception. Verify continuous Cyber coverage 4/1/2023 – 4/1/2025. Risk 8/25 if continuous; 22/25 if a gap exists.
>
> 8. **Named Insured "Runbeck Election Services, LLC"** — CORRECT entity type. This is the ONLY policy in the Runbeck program with correct LLC notation. The Policy Change #1 endorsement dated 4/1/2025 is the Name Change that added Properties/Investments/Graphics — evidence the broker/carrier knew the correct entity type and propagation to the other 6 program policies was missed. Asymmetry finding — risk 24/25 against the OTHER policies, informational on this Cyber policy.

## Related KB files
- GAP-08 umbrella-structure-EXPANDED.md (umbrella attachment over cyber)
- GAP-17 contract-specific-coverage-satisfaction.md
- GAP-18 coverage-specific-sublimits.md
