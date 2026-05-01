# Cancellation Notice Verification (EXPANDED)

## Purpose
Verify that the policy's cancellation AND nonrenewal notice periods meet the client's contractual and operational benchmarks, AND that all client contract counterparties appear in the designated-entity notice schedule, **with separate per-coverage-line benchmarks because Auto, Umbrella, and Package commonly have different baseline notice periods.**

## What's new in this expanded version
This file previously treated "cancellation notice" as a single benchmark. It now also covers:
1. **Cancellation vs Nonrenewal as separate notices** with separate benchmarks
2. **Per-coverage-line baseline differences** — Commercial Auto base is 30 days, often extended to 60 via Broadening; Umbrella base is 60 days, often reduced to 45 via state amendatory; Package base is 30 days, often extended to 45 via state amendatory
3. **Three-layer governance** — Common Conditions → State amendatory → Designated Entity schedule, each potentially overriding the other
4. **Designated Entity per-coverage-line check** is now its own KB file (GAP-21); this file focuses on the Named Insured notice

## Why it matters
Many state government vendor contracts require advance notice of any insurance cancellation. If the policy delivers less than the contract requires, the client is in technical breach. The per-coverage-line nuance matters because:
- A 30-day Auto notice combined with a 60-day Package notice means the same client has different protections on different coverages
- A state amendatory endorsement that EXTENDS notice on one line may simultaneously REDUCE notice on another (Arizona reduces Umbrella from 60 to 45 days)
- Cancellation and Nonrenewal are governed by different endorsements — a policy with 60-day cancellation notice may have only 30-day nonrenewal notice (Hanover 461-0505 in Arizona is the common example)

## Detection rules

### Rule 1 — Extract notice periods from all governing forms
Three layers typically govern cancellation:
1. **Common Policy Conditions (ISO IL 00 17 or carrier equivalent):** standard 10-day nonpayment / 30-day any-other-reason
2. **State amendatory endorsement (e.g., AZ IL 02 58, CA CP 01 40, TX IL 01 46):** typically supersedes the Common Conditions with a longer notice period for "other" cancellations (often 45 or 60 days)
3. **Carrier broadening endorsement (e.g., Hanover 461-0155 §1 for Auto extending base 30 to 60):** carrier-specific extension above the state amendatory baseline

### Rule 2 — Extract nonrenewal notice as a separate item
Nonrenewal is governed by a different endorsement than cancellation. Look for state-specific forms:
- AZ: Hanover 461-0505 Arizona Changes – Nonrenewal (30-day notice)
- Other states: similar amendatory forms

A policy can have 60-day cancellation notice and 30-day nonrenewal notice simultaneously — both must be checked.

### Rule 3 — Compare per-coverage-line to client benchmark
Take the longer of the three layers as the effective notice to the Named Insured for that specific coverage. Compare to the client's benchmark:

| Coverage line | Typical base (ISO) | Typical state-extended | Typical carrier-extended | Industry best |
|---|---|---|---|---|
| Commercial Auto | 30 days | 30 days | 60 days (via 461-0155) | 90 days |
| Commercial Package | 30 days | 45 days (AZ IL 02 58) | 45 days | 90 days |
| Commercial Umbrella | 60 days | 45 days (AZ — REDUCED) | 60 days | 90 days |
| Workers Comp | 30 days | 30 days | 30 days | 60 days |
| Cyber | varies | varies | varies | 60 days |

Note: Arizona is unusual in **reducing** the Umbrella base from 60 to 45 days. Check carefully when state amendatory is in play.

### Rule 4 — Designated Entity schedule check
For customer-contract-specific cancellation notice obligations, see GAP-21 (Designated Entity Cancellation Notice — Per-Policy-Type Coverage). This is a separate but related concern.

### Rule 5 — Check for nonrenewal notice gap
Even when cancellation notice is adequate, nonrenewal notice often falls short. A policy that delivers 60-day cancellation but only 30-day nonrenewal means the insured has only 30 days at year-end to find a replacement carrier — far below the typical 90-day client benchmark.

## Severity scoring
- **Critical (Ugly / 20–25):** Cancellation notice on any single coverage line is below contract requirement, AND missing Designated Entity schedule for customer counterparties
- **Critical (Ugly / 20–25):** Nonrenewal notice is below 30 days on any coverage line in a non-statutory state
- **Needs Attention (Bad / 9–19):** Cancellation notice meets contract minimum but is below 90-day industry benchmark
- **Needs Attention (Bad / 9–19):** Cancellation and nonrenewal notice differ significantly (e.g., 60 vs 30) — flag the shorter as the operational reality
- **Informational (Good / 1–8):** Cancellation and nonrenewal both ≥ 90 days on all coverage lines

## Example flagged finding
> Hanover Commercial Auto AW4-H221414-05 cancellation notice: base ISO IL 00 17 §A.2 says 30 days, extended by Hanover Broadening Endorsement 461-0155 §1 to 60 days. Nonrenewal notice via Hanover Arizona Changes 461-0505 is 30 days. Effective notice to Named Insured: 60-day cancellation, 30-day nonrenewal. Client benchmark per executive presentation Slide 18: 90 days. Cancellation falls 30 days short of benchmark; nonrenewal falls 60 days short. Plus: this policy has NO Designated Entity Cancellation Notice endorsement (cross-reference GAP-21) — customer counties listed on the Commercial Package via 401-1235 are absent from the Auto. Risk score 22/25.

## Related KB files
- GAP-17 contract-specific-coverage-satisfaction.md (per-coverage-line contract requirements)
- GAP-21 designated-entity-cancellation-notice.md (per-policy-type designated entity check)
