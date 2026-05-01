# Named Driver Exclusions and Cross-HR Risk

## Purpose
Detect Named Driver Exclusion endorsements on Commercial Auto policies and flag the operational/HR risk they create. A named driver exclusion completely voids Liability, Medical Payments, and Physical Damage coverage for any accident involving the excluded individual driving a covered auto, with limited givebacks for UM/UIM only.

## Why it matters
Named Driver Exclusions are typically carrier-imposed in response to MVR violations, license issues, or claims history. They are easy to overlook because they're buried in the endorsement schedule rather than the Dec. The risk is binary and severe: **a single accident involving the excluded driver in a covered vehicle leaves the insured fully exposed for the loss, with no defense, no indemnity, and no physical damage payout.**

The cross-HR risk dimension: if the excluded individual is still an active employee with potential vehicle access, every shift creates exposure. If the individual has separated from the company but the exclusion remains on the policy, it's an administrative cleanup item but no longer a live risk. The tool should distinguish these states.

## Detection rules

### Rule 1 — Identify the exclusion endorsement
Look for forms by these names or numbers:
- ISO CA 99 99 (Named Driver Exclusion)
- State-specific forms (e.g., Hanover 461-0425 Arizona Exclusion of Named Driver, 9/10 edition)
- Carrier-specific equivalents

Trigger phrases in the schedule:
- "Name of Individual(s):" followed by a person's name
- "the insurance afforded by this policy does not apply to any 'accident' or 'loss' resulting from the operation or use of any covered 'auto' by the individual named"

### Rule 2 — Identify the giveback (typically UM/UIM)
Most state forms preserve UM/UIM coverage for the excluded driver as a victim. Confirm this language is present:
- "...with the exception of Uninsured Motorist Coverage and Underinsured Motorist Coverage"

If UM/UIM giveback is NOT present, severity escalates because the excluded individual has no recovery if they're injured by an uninsured third party while in the covered auto.

### Rule 3 — Output an HR/operational verification request
The tool cannot determine employment status from the policy alone. Output a structured question for the producer/insured:
- Is [name] currently employed by the insured?
- If yes, does the role include any access to covered vehicles (regular driver, occasional driver, parking lot, after-hours)?
- If yes, is there a documented HR control preventing vehicle access?
- If no longer employed, when did employment end? (Document for renewal-cycle removal of the endorsement.)

### Rule 4 — Flag rare cases of multiple named exclusions
A single excluded driver often reflects an MVR issue. Multiple excluded drivers on a small fleet suggests systemic underwriting concerns the carrier is trying to manage — flag as a renewal-strategy issue (carrier may non-renew or radically reprice).

## Severity scoring
- **Critical (Ugly / 20–25):** Excluded individual is a current employee with confirmed or possible vehicle access AND no documented HR control preventing access
- **Needs Attention (Bad / 9–19):** Excluded individual is a current employee, vehicle access uncertain — output verification request
- **Needs Attention (Bad / 9–19):** Multiple individuals excluded on a small (<10 vehicle) fleet — renewal risk
- **Informational (Good / 1–8):** Excluded individual is no longer employed — recommend endorsement removal at renewal

## Example flagged finding
> Hanover Auto AW4-H221414-05 includes Form 461-0425 (9/10) — Arizona Exclusion of Named Driver. The schedule excludes **MALINA TRUJILLO**. Liability, Medical Payments, and Physical Damage do not apply to any accident involving this individual driving a covered auto; only UM/UIM coverage is preserved. **Verify with insured: is Malina Trujillo currently employed? If yes, does her role include vehicle access? If no, when did employment end and can the endorsement be removed at renewal?** Risk score pending HR confirmation: 22/25 if currently employed with vehicle access, 8/25 if separated.
