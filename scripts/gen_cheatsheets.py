"""
gen_cheatsheets.py -- Generate KB cheat-sheet PDFs for cyber, D&O, EPLI, E&O, and WC.

Run from repo root:
    python scripts/gen_cheatsheets.py
"""

from pathlib import Path
from fpdf import FPDF

KB = Path(__file__).parent.parent / "knowledge-base" / "by-coverage"

# ── Colour palette ───────────────────────────────────────────────────
NAVY   = (13,  71, 161)    # section headers
RED    = (183,  28,  28)   # Ugly / critical
ORANGE = (230, 81,   0)    # Bad / warning
GREEN  = (27, 94,  32)     # Good / ok
GREY   = (97,  97,  97)    # body text
BLACK  = (33,  33,  33)    # titles
WHITE  = (255, 255, 255)


class Sheet(FPDF):
    """Cheat-sheet base class with consistent header/footer/helpers."""

    def __init__(self, title: str, subtitle: str):
        super().__init__()
        self.doc_title    = title
        self.doc_subtitle = subtitle
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(True, margin=15)

    def header(self):
        # Navy bar
        self.set_fill_color(*NAVY)
        self.rect(0, 0, 210, 12, "F")
        self.set_xy(15, 2)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*WHITE)
        self.cell(0, 8, self.doc_title.upper(), ln=False)
        self.set_xy(0, 2)
        self.set_font("Helvetica", "", 7)
        self.cell(195, 8, "BOGDAN LAZA, CLCS  |  PATRIOT GROWTH INSURANCE SERVICES", align="R")
        self.set_text_color(*BLACK)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*GREY)
        self.cell(0, 8, f"Page {self.page_no()} -- {self.doc_subtitle}", align="C")
        self.set_text_color(*BLACK)

    # ── Layout helpers ───────────────────────────────────────────────

    def title_block(self):
        self.ln(6)
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*NAVY)
        self.cell(0, 10, self.doc_title, ln=True)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*GREY)
        self.cell(0, 6, self.doc_subtitle, ln=True)
        self.set_text_color(*BLACK)
        self.ln(3)
        self.set_draw_color(*NAVY)
        self.set_line_width(0.6)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(4)

    def section(self, heading: str, color=None):
        color = color or NAVY
        self.ln(3)
        self.set_fill_color(*color)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 6, f"  {heading.upper()}", ln=True, fill=True)
        self.set_text_color(*BLACK)
        self.ln(1)

    def bullet(self, text: str, indent: int = 5, color=None):
        color = color or BLACK
        x = self.get_x()
        self.set_x(15 + indent)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*color)
        # bullet character
        self.set_font("Helvetica", "B", 9)
        self.cell(4, 5, "*", ln=False)
        self.set_font("Helvetica", "", 8)
        self.multi_cell(0, 5, text)
        self.set_text_color(*BLACK)

    def sub_bullet(self, text: str):
        self.set_x(24)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*GREY)
        self.cell(4, 4.5, "-", ln=False)
        self.multi_cell(0, 4.5, text)
        self.set_text_color(*BLACK)

    def flag(self, label: str, text: str, sev: str = "bad"):
        """Inline flag line: coloured label + text."""
        colors = {"ugly": RED, "bad": ORANGE, "good": GREEN}
        c = colors.get(sev, ORANGE)
        self.set_x(15)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*c)
        self.cell(22, 5, f"[{label.upper()}]", ln=False)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*BLACK)
        self.multi_cell(0, 5, text)

    def note(self, text: str):
        self.set_x(15)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*GREY)
        self.multi_cell(0, 4.5, text)
        self.set_text_color(*BLACK)

    def two_col(self, left_lines: list, right_lines: list, heading_l="", heading_r=""):
        """Two-column block."""
        col_w = 85
        gap   = 10
        x0    = 15
        x1    = x0 + col_w + gap
        y0    = self.get_y()

        def col_block(x, heading, lines):
            self.set_xy(x, y0)
            if heading:
                self.set_font("Helvetica", "B", 8)
                self.set_text_color(*NAVY)
                self.cell(col_w, 5, heading, ln=True)
                self.set_text_color(*BLACK)
                self.set_x(x)
            for ln in lines:
                self.set_font("Helvetica", "", 7.5)
                self.set_x(x)
                self.cell(4, 4.5, "*", ln=False)
                self.multi_cell(col_w - 4, 4.5, ln)
                self.set_x(x)

        y_before = self.get_y()
        col_block(x0, heading_l, left_lines)
        y_after_l = self.get_y()
        col_block(x1, heading_r, right_lines)
        y_after_r = self.get_y()
        self.set_y(max(y_after_l, y_after_r) + 2)


# ══════════════════════════════════════════════════════════════════════
#  1. CYBER LIABILITY CHEAT SHEET
# ══════════════════════════════════════════════════════════════════════

def make_cyber():
    pdf = Sheet(
        "Cyber Liability Coverage Cheat Sheet",
        "Key audit criteria for standalone cyber and tech-combined policies"
    )
    pdf.add_page()
    pdf.title_block()

    pdf.section("What kind of policy is this? -- First Pass")
    pdf.bullet("Standalone Cyber vs. Tech E&O + Cyber combined -- identify the form")
    pdf.bullet("Claims-made form -- note the retroactive date and extended reporting period (ERP/tail)")
    pdf.bullet("Check declarations for sublimits -- ransomware/extortion, social engineering, and BI often carry separate, lower limits")
    pdf.bullet("Verify the carrier is rated A- or better (AM Best) -- E&S placement is common but check concentration risk")

    pdf.section("First-Party Coverage -- What the Policy Pays Directly")
    pdf.bullet("Data restoration / system recovery costs -- is there a per-occurrence sublimit?")
    pdf.sub_bullet("Watch for: restoration limited to last known backup state (leaves gap for data that predates backup)")
    pdf.bullet("Business interruption / extra expense -- trigger is critical")
    pdf.sub_bullet("Some forms require a 'system failure' trigger; others require actual breach -- know which")
    pdf.sub_bullet("Waiting period / retention (often 8-12 hours) before BI coverage kicks in")
    pdf.sub_bullet("Dependent business interruption -- does the policy cover BI from a vendor outage (e.g., AWS goes down)?")
    pdf.bullet("Ransomware / cyber extortion -- is this a sublimit or full limit?")
    pdf.sub_bullet("Does the policy require carrier approval BEFORE paying ransom? (Creates timing conflict during active attack)")
    pdf.bullet("Crisis management / notification costs -- regulatory notification, credit monitoring, PR firm")
    pdf.bullet("Social engineering / funds transfer fraud -- these are frequently sublimited to $250k-$500k even on $5M cyber towers")
    pdf.sub_bullet("Check: does it require the insured to verify the transfer request? (Conditions can void coverage if skipped)")

    pdf.section("Third-Party Coverage -- What the Policy Pays to Others")
    pdf.bullet("Network security liability -- failure to prevent transmission of malware, denial of service attack, unauthorized access")
    pdf.bullet("Privacy liability -- breach of PII, PHI, or confidential corporate data")
    pdf.bullet("Media liability -- defamation, copyright infringement in online content (often included; confirm scope)")
    pdf.bullet("Regulatory defense and fines -- HIPAA, CCPA, GDPR, state AG actions")
    pdf.sub_bullet("CRITICAL: Some policies exclude fines/penalties in states where insuring fines is prohibited by law -- verify applicable jurisdiction")
    pdf.sub_bullet("PCI-DSS assessments and card brand fines -- these are NOT automatic; look for explicit PCI coverage grant")

    pdf.add_page()
    pdf.section("The Retroactive Date -- Most Common Gap")
    pdf.flag("UGLY", "Retroactive date later than the company's founding or last known clean audit -- prior incidents not covered", "ugly")
    pdf.flag("UGLY", "Gap between policy periods (even 1 day) where no prior acts coverage exists -- attaches to claims-made trigger", "ugly")
    pdf.flag("BAD",  "Short ERP (90 days) on a non-renewed policy -- claims reported after expiration from incidents before expiration are uninsured", "bad")
    pdf.bullet("Compare retroactive date to: company founding date, last major system change, any known incidents")
    pdf.bullet("If the company has had cyber coverage continuously, retroactive date should match original inception date")
    pdf.bullet("If switching carriers, prior carrier's ERP must cover the gap until new retroactive date kicks in")

    pdf.section("Key Exclusions -- What the Policy Won't Pay")
    pdf.bullet("War / nation-state exclusion -- increasingly broad; some carriers exclude any incident attributable to a government actor")
    pdf.sub_bullet("The NotPetya / Merck situation: exclusion tested in court; outcome favored insured but new forms tightened language")
    pdf.bullet("Infrastructure failure exclusion -- power grid outage, internet backbone failure (no malicious actor required)")
    pdf.bullet("Prior knowledge exclusion -- any circumstance known before inception that should have been disclosed")
    pdf.bullet("Betterment exclusion -- carrier won't pay to restore systems to a better state than before the loss")
    pdf.bullet("Unencrypted devices -- some forms deny data liability coverage if the lost device was unencrypted")
    pdf.bullet("Contractual liability exclusion -- assumes liability beyond what you'd have absent the contract")
    pdf.bullet("Employee dishonesty / insider threat -- often sublimited or excluded; may need Crime policy supplement")

    pdf.section("Contract Requirements Check")
    pdf.bullet("Does the client's MSA/contract require cyber coverage? Note: 'Technology E&O' and 'Cyber' are different; contracts often specify both")
    pdf.bullet("Additional Insured on cyber is uncommon but contract may require it -- check if form allows it")
    pdf.bullet("Contractual minimum limits: $1M per occurrence is common for tech vendors; $5M+ for healthcare/financial")
    pdf.bullet("Notice of cancellation: 30-day notice is standard; some government contracts require 60 days")

    pdf.section("Quick Rating: Good / Bad / Ugly Triggers")
    pdf.flag("UGLY", "No standalone cyber; only cyber endorsement on BOP/Package for a company handling PII or PHI", "ugly")
    pdf.flag("UGLY", "Retroactive date gap or unknown retro date -- treat as no prior acts coverage", "ugly")
    pdf.flag("UGLY", "Social engineering sublimit <$250k for a company with regular wire transfers", "ugly")
    pdf.flag("BAD",  "BI waiting period >24 hours for a company whose revenue is entirely online", "bad")
    pdf.flag("BAD",  "No dependent BI coverage for a company whose operations depend on a cloud provider", "bad")
    pdf.flag("BAD",  "PCI fines not covered for a company processing credit cards", "bad")
    pdf.flag("GOOD", "Full limit applies to ransomware (no sublimit), carrier pre-approved crisis vendor panel", "good")
    pdf.flag("GOOD", "Retroactive date matches company inception, continuous coverage, 12-month ERP available", "good")

    out = KB / "cyber" / "01_cyber-coverage-cheat-sheet.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))
    print(f"  Created: {out}")


# ══════════════════════════════════════════════════════════════════════
#  2. D&O CHEAT SHEET
# ══════════════════════════════════════════════════════════════════════

def make_do():
    pdf = Sheet(
        "Directors & Officers (D&O) Coverage Cheat Sheet",
        "Key audit criteria -- Management Liability package or standalone D&O"
    )
    pdf.add_page()
    pdf.title_block()

    pdf.section("Policy Structure -- Side A / B / C")
    pdf.bullet("Side A -- Individual directors and officers when the entity CANNOT indemnify (insolvency, prohibited by law)")
    pdf.sub_bullet("Most critical for individuals personally -- should have highest priority in loss scenarios")
    pdf.sub_bullet("Excess Side A / DIC (Difference-in-Conditions) is a separate tower that pays when the primary policy is exhausted or rescinded")
    pdf.bullet("Side B -- Reimburses the entity when it HAS indemnified its directors and officers")
    pdf.bullet("Side C -- Entity Securities Coverage: protects the company itself against securities claims")
    pdf.sub_bullet("Side C is only meaningful for public companies (SEC/exchange-listed); private companies often have 'Entity Coverage' instead, covering the entity against D&O-type claims")
    pdf.bullet("Check: Is entity coverage included? Private companies need this to cover the company against shareholder derivative suits or investor claims")
    pdf.flag("UGLY", "No Side A coverage -- individuals personally exposed when company cannot indemnify (bankruptcy scenario)", "ugly")
    pdf.flag("BAD",  "No entity coverage for a private company with outside investors or lenders who could sue", "bad")

    pdf.section("Insured vs. Insured Exclusion -- Most Litigated D&O Exclusion")
    pdf.bullet("Excludes claims brought BY one insured AGAINST another insured")
    pdf.sub_bullet("Classic trap: shareholder-director sues the company and other directors -- excluded under broad IvI language")
    pdf.bullet("Carve-outs to look for (each reduces the gap):")
    pdf.sub_bullet("Derivative suits brought by shareholders in their capacity as shareholders (not as directors)")
    pdf.sub_bullet("Claims by former directors/officers (departed insured should not bar coverage)")
    pdf.sub_bullet("Bankruptcy trustee or examiner claims (trustee is not acting as an insured)")
    pdf.sub_bullet("Employment-related claims (should be carved back to EPLI trigger, not excluded by IvI)")
    pdf.flag("UGLY", "IvI exclusion with no carve-out for derivative suits or bankruptcy trustee claims -- common gap on cheaper forms", "ugly")
    pdf.flag("BAD",  "IvI exclusion that captures former officers -- departures create immediate coverage gap", "bad")

    pdf.section("Prior/Pending Litigation Date")
    pdf.bullet("Excludes any claim arising out of a circumstance KNOWN before the prior/pending date")
    pdf.bullet("Different from retroactive date -- it's tied to knowledge, not timing of act")
    pdf.bullet("Check: Does the prior/pending date match policy inception or is it earlier?")
    pdf.flag("UGLY", "Prior/pending date is years before inception -- any disclosed circumstance from that period is permanently excluded", "ugly")
    pdf.flag("BAD",  "Company had litigation or regulatory investigation within the prior/pending window that was not disclosed -- creates rescission risk", "bad")
    pdf.bullet("Ask: Any pending lawsuits, regulatory inquiries, or SEC/DOJ contact? All must be disclosed at inception")

    pdf.add_page()
    pdf.section("Bump-Up Exclusion (M&A Transactions)")
    pdf.bullet("Excludes claims alleging inadequate consideration in a merger or acquisition")
    pdf.sub_bullet("If shareholders sue saying the buyout price was too low -- bump-up exclusion bars coverage")
    pdf.bullet("Relevant for any company that has been acquired, is being acquired, or has done acquisitions")
    pdf.bullet("Some carriers offer a carve-back for defense costs even when bump-up excludes indemnity")
    pdf.flag("BAD", "Bump-up exclusion with no defense cost carve-back -- directors exposed to personal legal fees in M&A litigation", "bad")

    pdf.section("Investigation Costs / Pre-Claim Inquiry Coverage")
    pdf.bullet("D&O policies vary widely on whether investigation costs are covered BEFORE a formal 'Claim' is made")
    pdf.sub_bullet("Regulatory subpoena, DOJ CID (Civil Investigative Demand), grand jury subpoena -- are these 'Claims'?")
    pdf.sub_bullet("SEC informal inquiry vs. formal order of investigation -- which triggers coverage?")
    pdf.bullet("Look for: 'Securities investigation coverage,' 'pre-claim inquiry' grants, or explicit inclusion of subpoenas in 'Claim' definition")
    pdf.flag("BAD", "Investigation costs not covered until formal charge filed -- investigation itself can cost $500k+ in legal fees", "bad")
    pdf.flag("GOOD", "Broad 'Claim' definition that includes written demands, regulatory subpoenas, and formal investigations", "good")

    pdf.section("Definition of 'Claim' -- Broadest Possible is Best")
    pdf.bullet("Narrow definition: only formal lawsuits or written demands for monetary damages")
    pdf.bullet("Broad definition: includes regulatory investigations, subpoenas, administrative proceedings, written demand for non-monetary relief")
    pdf.bullet("PE-backed companies: look for 'Claim' to include demands by investors or board observers in their capacity as owners")
    pdf.bullet("SPAC transactions: check for specific SPAC/de-SPAC claim triggers -- increasingly litigated")

    pdf.section("Entity Liability -- What the Company Itself is Covered For")
    pdf.bullet("Private company entity coverage: claims against the company (not just directors) for management decisions")
    pdf.bullet("Check exclusions on entity coverage -- some policies carve out bodily injury, property damage (should be on GL/umbrella)")
    pdf.bullet("Employment-related claims against the entity -> should be EPLI, not D&O entity")
    pdf.flag("BAD", "Entity coverage has broad contractual liability exclusion -- investor agreements, shareholder agreements could be excluded", "bad")

    pdf.section("Quick Rating Triggers")
    pdf.flag("UGLY", "No D&O at all for a company with outside investors, a board, or PE/VC backing", "ugly")
    pdf.flag("UGLY", "IvI exclusion bars derivative suits with no carve-out -- core D&O exposure uninsured", "ugly")
    pdf.flag("UGLY", "Claims-made policy with no ERP available at renewal -- any non-renewed circumstance permanently uninsured", "ugly")
    pdf.flag("BAD",  "Low limit ($1M) for a PE-backed portfolio company -- investor-related claims routinely exceed $5M in defense costs alone", "bad")
    pdf.flag("BAD",  "Prior/pending date coincides with a known investigation -- potential rescission exposure", "bad")
    pdf.flag("GOOD", "Broad Claim definition, IvI carve-outs for derivative suits and bankruptcy, excess Side A tower", "good")

    out = KB / "do-epli" / "01_DO-coverage-cheat-sheet.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))
    print(f"  Created: {out}")


# ══════════════════════════════════════════════════════════════════════
#  3. EPLI CHEAT SHEET
# ══════════════════════════════════════════════════════════════════════

def make_epli():
    pdf = Sheet(
        "Employment Practices Liability (EPLI) Cheat Sheet",
        "Key audit criteria -- standalone EPLI or Management Liability package"
    )
    pdf.add_page()
    pdf.title_block()

    pdf.section("Policy Structure -- Standalone vs. Package")
    pdf.bullet("EPLI is often bundled in a Management Liability package (D&O + EPLI + Crime + Fiduciary)")
    pdf.bullet("Bundled policies share a single aggregate limit -- a large D&O claim can exhaust the limit before EPLI claims are paid")
    pdf.sub_bullet("Companies with significant employment exposure (high headcount, multi-state, unions) should consider standalone EPLI with its own limit")
    pdf.bullet("Claims-made form -- note retroactive date (should go back to company founding or last clean audit) and ERP availability")

    pdf.section("Definition of 'Employee' -- The Coverage Scope Gate")
    pdf.bullet("Narrow definition: only W-2 full-time employees of the named insured")
    pdf.bullet("Broad definition: includes part-time, seasonal, temporary, leased, and independent contractors")
    pdf.flag("UGLY", "Company uses significant temp/staffing agency workers or classifies workers as 1099 contractors -- if they are excluded from 'Employee' definition, misclassification claims are uninsured", "ugly")
    pdf.flag("BAD",  "Client uses staffing agencies but has no Alternate Employer or additional insured arrangement -- staffing agency workers can still sue the host employer", "bad")
    pdf.bullet("Check state-specific requirements: California AB5, New York's expanded worker definitions dramatically increase exposure")
    pdf.bullet("Volunteer workers: nonprofits especially need volunteers included in definition")

    pdf.section("Third-Party Harassment Coverage")
    pdf.bullet("Standard EPLI covers claims BY employees AGAINST the employer")
    pdf.bullet("Third-party harassment covers claims by CUSTOMERS, VENDORS, or MEMBERS OF THE PUBLIC against the insured for harassment by its employees")
    pdf.sub_bullet("Restaurant workers, hotel staff, rideshare drivers -- third-party exposure is real and frequently excluded")
    pdf.flag("BAD", "Client has customer-facing workforce (retail, hospitality, healthcare) with no third-party EPLI coverage", "bad")
    pdf.flag("GOOD", "Third-party coverage endorsed onto policy; definition of 'Third Party' is broad (customers, vendors, patients)", "good")

    pdf.section("Wage & Hour Claims -- The Most Common Exclusion")
    pdf.bullet("EPLI policies almost universally EXCLUDE wage & hour claims (overtime, minimum wage, meal/rest break violations)")
    pdf.sub_bullet("Class action wage & hour suits are the most common employment claim in California and increasingly other states")
    pdf.bullet("Some carriers offer wage & hour defense cost coverage as an endorsement (NOT indemnity -- just legal defense)")
    pdf.sub_bullet("Typical sublimit: $100k-$500k for defense costs only; no coverage for settlement amounts")
    pdf.flag("UGLY", "Multi-state employer with no wage & hour defense coverage -- California exposure alone can be $1M+ in defense costs before settlement", "ugly")
    pdf.flag("BAD",  "Wage & hour endorsement available but not purchased -- ask why", "bad")
    pdf.bullet("FLSA (Federal) vs. state wage claims: federal exposure is real but state laws (CA, NY, WA) are worse")

    pdf.add_page()
    pdf.section("Prior/Pending Exclusion")
    pdf.bullet("Excludes claims arising from circumstances known before the prior/pending date")
    pdf.bullet("Ask at intake: Any pending EEOC charges, litigation, or formal complaints? All must be disclosed")
    pdf.flag("UGLY", "Active EEOC charge or lawsuit that was not disclosed at inception -- carrier has rescission grounds", "ugly")
    pdf.bullet("Unlike D&O, EPLI prior/pending date is typically the policy inception date (not a separate retroactive date)")
    pdf.bullet("Continuity clause: if insured has had continuous EPLI coverage, prior/pending should match original inception year")

    pdf.section("Consent-to-Settle / Hammer Clause")
    pdf.bullet("Most EPLI policies require insured's consent before settling a claim")
    pdf.bullet("Hammer clause: if insured refuses a reasonable settlement, carrier's liability is capped at the refused settlement amount + defense costs to date of refusal")
    pdf.sub_bullet("'Soft' hammer: insured retains consent right but carrier pays only 50-75% of excess costs above the refused settlement")
    pdf.sub_bullet("'Hard' hammer: insured's share is 100% of everything above the refused settlement -- significant financial exposure")
    pdf.flag("BAD", "Hard hammer clause -- insured can be forced to choose between settling a meritless claim or bearing full excess cost personally", "bad")
    pdf.flag("GOOD", "Mutual consent required; no hammer or soft hammer (50/50 split) if insured refuses reasonable settlement", "good")

    pdf.section("Defense Structure -- Duty to Defend vs. Consent")
    pdf.bullet("EPLI is almost always a 'consent-to-defend' (not duty-to-defend) form: insured selects counsel, carrier approves")
    pdf.bullet("Panel counsel vs. independent counsel: some carriers require use of their pre-approved employment defense firms")
    pdf.sub_bullet("If client already has a preferred employment law firm, confirm they are on the carrier's panel or that independent counsel is permitted")
    pdf.bullet("Defense costs inside vs. outside limits: most EPLI policies have defense costs eroding the limit")
    pdf.sub_bullet("A $1M EPLI policy with $400k in defense costs only has $600k left for settlement -- know this going in")
    pdf.flag("BAD", "Defense costs inside the limit for a company in a high-claim industry (staffing, healthcare) -- limit is effectively much lower than it appears", "bad")

    pdf.section("Quick Rating Triggers")
    pdf.flag("UGLY", "No EPLI coverage at all for a company with 5+ employees -- discrimination and harassment claims are near-universal exposure", "ugly")
    pdf.flag("UGLY", "California-based or multi-CA-location employer with no wage & hour defense endorsement", "ugly")
    pdf.flag("UGLY", "Significant temp/contractor workforce excluded from 'Employee' definition", "ugly")
    pdf.flag("BAD",  "Third-party harassment excluded for a customer-facing workforce", "bad")
    pdf.flag("BAD",  "Prior EEOC charge not disclosed -- rescission risk at claim time", "bad")
    pdf.flag("GOOD", "Broad employee definition, third-party coverage, wage & hour defense endorsement, soft hammer, defense costs outside the limit", "good")

    out = KB / "do-epli" / "02_EPLI-coverage-cheat-sheet.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))
    print(f"  Created: {out}")


# ══════════════════════════════════════════════════════════════════════
#  4. E&O / PROFESSIONAL LIABILITY CHEAT SHEET
# ══════════════════════════════════════════════════════════════════════

def make_eo():
    pdf = Sheet(
        "Professional Liability / E&O Coverage Cheat Sheet",
        "Key audit criteria -- claims-made form, service-industry exposure"
    )
    pdf.add_page()
    pdf.title_block()

    pdf.section("Claims-Made Mechanics -- The Trigger That Bites Everyone")
    pdf.bullet("A claims-made policy covers claims MADE during the policy period, regardless of when the act occurred (subject to retroactive date)")
    pdf.bullet("Three dates to verify on every E&O policy:")
    pdf.sub_bullet("1. Policy inception and expiration -- the 'claims window'")
    pdf.sub_bullet("2. Retroactive date -- the earliest covered act date; anything before this is excluded")
    pdf.sub_bullet("3. Extended Reporting Period (ERP / tail) -- extends claims window after policy expires")
    pdf.bullet("Occurrence-form E&O exists but is rare -- verify which trigger applies before analysis")
    pdf.flag("UGLY", "Retroactive date is not 'full prior acts' -- any work done before the retro date creates an uninsured gap", "ugly")
    pdf.flag("UGLY", "No ERP endorsement available at renewal -- coverage for acts done during policy period but claimed later is cut off at expiration", "ugly")
    pdf.flag("BAD",  "Retroactive date changed between carriers at renewal without matching ERP from prior carrier -- classic prior acts gap", "bad")

    pdf.section("Definition of 'Professional Services' -- The Scope Battle")
    pdf.bullet("E&O only covers claims arising from the DEFINED professional services -- read the definition carefully")
    pdf.bullet("Check: Does the definition match what the client ACTUALLY does today, not just at policy inception?")
    pdf.sub_bullet("Technology companies: does 'professional services' include software development, implementation, AND consulting? Or just one?")
    pdf.sub_bullet("Consulting firms: does 'advice' cover strategic/management consulting or only technical advice?")
    pdf.sub_bullet("Staffing firms: are staffing services (placing workers) covered, or only services performed BY the staffed workers?")
    pdf.flag("UGLY", "Company has expanded its services since inception and new service lines are outside the professional services definition", "ugly")
    pdf.flag("UGLY", "MSA requires coverage for services that don't match the policy's professional services definition", "ugly")
    pdf.flag("BAD",  "Vague or narrow definition that a carrier could argue excludes a material line of the insured's business", "bad")
    pdf.bullet("Quote exact policy language vs. the client's actual service description -- let the gap speak for itself")

    pdf.section("Prior Acts Date -- The Gap at the Start")
    pdf.bullet("If the retroactive date is the same as policy inception -> no prior acts coverage (many first-time buyers make this mistake)")
    pdf.bullet("'Full prior acts' means the retroactive date is blank or predates company founding -- this is the gold standard")
    pdf.bullet("Prior carrier's policy matters: if a company switches carriers, what happens to claims from acts under the old policy?")
    pdf.sub_bullet("Option A: Prior carrier provides ERP (tail) -- costs 100-200% of annual premium, covers old acts reported after expiration")
    pdf.sub_bullet("Option B: New carrier provides 'prior acts' coverage -- retroactive date set to old policy's inception date")
    pdf.sub_bullet("If neither: there is a gap for acts done under the old policy period that are claimed after expiration")
    pdf.flag("UGLY", "Company switched E&O carriers with no ERP from prior carrier AND no prior acts coverage from new carrier", "ugly")

    pdf.add_page()
    pdf.section("Duty to Defend vs. Right to Defend")
    pdf.bullet("Duty to Defend (DDef): carrier MUST defend the insured, even if the underlying claim is ultimately excluded")
    pdf.sub_bullet("Better for the insured -- carrier pays defense costs from dollar one, even on questionable claims")
    pdf.bullet("Right to Defend (RDef): carrier has the RIGHT to defend but can choose not to if the claim appears excluded")
    pdf.sub_bullet("In practice, carrier may refuse or delay engaging counsel until coverage is confirmed")
    pdf.bullet("Most professional liability policies are RIGHT-to-defend forms")
    pdf.flag("BAD", "Right-to-defend form for a client in a highly litigious industry (tech, healthcare, financial services) -- out-of-pocket defense costs in coverage disputes can be significant", "bad")
    pdf.flag("GOOD", "Duty-to-defend form -- carrier defends even while reserving rights, insured doesn't fund defense out-of-pocket", "good")

    pdf.section("Hammer Clause / Consent to Settle")
    pdf.bullet("Insured's consent required before carrier can settle -- this is standard on E&O forms")
    pdf.bullet("Hard hammer: if insured refuses a reasonable settlement, insured bears 100% of everything above the refused amount")
    pdf.bullet("Soft hammer: typically 50/50 or 70/30 split above the refused settlement -- more common on modern forms")
    pdf.bullet("'Cooperation clause' can have same effect -- insured who refuses to cooperate in settlement loses coverage")
    pdf.flag("BAD", "Hard hammer on a policy where the insured routinely defends on principle -- one stubborn defense decision can exceed the entire policy limit", "bad")

    pdf.section("Subcontractor / Third-Party Providers")
    pdf.bullet("Does the policy cover work performed BY subcontractors on the insured's behalf?")
    pdf.sub_bullet("If the insured uses subs and the subs' errors create a claim against the insured -- is that covered?")
    pdf.bullet("Some policies exclude subcontractor work entirely; others include it but only if the insured is named as a defendant (vicarious liability)")
    pdf.bullet("MSAs often make the insured responsible for their subs' work -- verify the E&O form covers that exposure")
    pdf.flag("UGLY", "Insured uses subcontractors for a material portion of client work; policy excludes subcontractor-related claims; MSA makes insured liable for sub errors", "ugly")
    pdf.flag("GOOD", "Policy explicitly covers acts of subcontractors and independent contractors performing services on behalf of the insured", "good")

    pdf.section("Tail / ERP Provisions")
    pdf.bullet("Extended Reporting Period (ERP / tail) extends the claims window after the policy expires")
    pdf.sub_bullet("1-year tail: typically 100% of the annual premium")
    pdf.sub_bullet("3-year tail: typically 150-200% of annual premium")
    pdf.sub_bullet("Automatic ERP: some policies include a short (60-90 day) automatic ERP -- check if it's there")
    pdf.bullet("When is tail critical? Company sale, principal retirement, policy non-renewal, carrier exit from the market")
    pdf.bullet("Some policies include a 'free tail' provision for death, disability, or retirement of named insured -- verify")
    pdf.flag("BAD", "Company being acquired and no tail has been purchased -- acquiring entity may not extend E&O coverage to target company's prior acts", "bad")

    pdf.section("Quick Rating Triggers")
    pdf.flag("UGLY", "Retroactive date = policy inception date (no prior acts) -- all historical work is uninsured", "ugly")
    pdf.flag("UGLY", "Professional services definition materially narrower than actual business operations", "ugly")
    pdf.flag("UGLY", "Prior carrier relationship ended with no ERP and no prior acts pickup from new carrier", "ugly")
    pdf.flag("BAD",  "Subcontractor exclusion for a company whose delivery model depends on subs", "bad")
    pdf.flag("BAD",  "Hard hammer clause on a principle-driven defense culture", "bad")
    pdf.flag("GOOD", "Full prior acts, broad professional services definition matching actual operations, subcontractor coverage included, soft hammer or no hammer, ERP available", "good")

    out = KB / "professional-liability" / "01_EO-coverage-cheat-sheet.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))
    print(f"  Created: {out}")


# ══════════════════════════════════════════════════════════════════════
#  5. WORKERS COMP FAST-SCAN CHEAT SHEET
# ══════════════════════════════════════════════════════════════════════

def make_wc():
    pdf = Sheet(
        "Workers Compensation -- 7-Point Fast Scan",
        "Quick audit checklist -- flag the issues worth flagging, skip the rest"
    )
    pdf.add_page()
    pdf.title_block()

    pdf.note(
        "WC is a statutory line -- carriers can't deny most WC claims on coverage grounds. "
        "The real audit questions are: (1) Is every state covered? (2) Are classifications accurate "
        "enough to avoid a premium audit surprise? (3) Are contractual WC requirements met?"
    )
    pdf.ln(3)

    pdf.section("1. Covered States List -- The Only Truly Ugly WC Finding")
    pdf.bullet("Check Item 3.A. on the Information Page -- lists states where coverage is provided")
    pdf.bullet("Compare against: where the insured has payroll, employees, or regular operations")
    pdf.flag("UGLY", "State where the insured has employees is MISSING from Item 3.A. -- those employees have no WC coverage, insured faces statutory penalties and uninsured employer liability", "ugly")
    pdf.bullet("Item 3.C. -- 'Other States' endorsement: covers employees who travel to or work temporarily in unlisted states")
    pdf.sub_bullet("Should be broad (list all unlisted states or 'All states except monopolistic') for companies with traveling employees")
    pdf.flag("BAD", "No Other States endorsement and employees regularly work in multiple states -- any assignment to an unlisted state creates a gap", "bad")
    pdf.bullet("Monopolistic states (ND, OH, WA, WY) require coverage through the state fund -- cannot be added to a private policy")
    pdf.sub_bullet("Verify: does the insured have operations in a monopolistic state? If so, confirm state fund coverage exists separately")

    pdf.section("2. Classification Codes vs. Actual Operations")
    pdf.bullet("Check Item 4 (Classification of Operations) on the Information Page against what the company actually does")
    pdf.bullet("Purpose: verify payroll is assigned to the correct codes -- wrong codes = wrong premium, potential audit adjustment")
    pdf.bullet("Do NOT flag classification code phraseology as an 'Ugly' finding without confirming the code itself is wrong")
    pdf.sub_bullet("NCCI codes often have generic phraseology that doesn't perfectly match the operation description -- the code may still be correct")
    pdf.sub_bullet("Same code appearing in multiple states = deliberate underwriter choice, not repeated error")
    pdf.flag("BAD", "High-hazard operations (roofing, structural steel, demolition) classified under a lower-hazard code -- actual premium is understated, audit adjustment likely", "bad")
    pdf.flag("BAD", "Office employees classified under a field operations code (or vice versa) -- overstatement is also a problem (overpaying)", "bad")
    pdf.note("Always note: 'Verify with carrier/NCCI' rather than declaring the code definitively wrong without NCCI lookup.")

    pdf.section("3. Experience Modification Rate (EMOD)")
    pdf.bullet("Find EMOD on the Information Page (may be listed as 'Experience Modification' or as a named endorsement)")
    pdf.bullet("EMOD > 1.00 = worse than average loss history; EMOD < 1.00 = better than average")
    pdf.bullet("An EMOD of 1.15+ on a construction risk is a material finding -- premium is 15%+ above baseline, signaling a loss control problem")
    pdf.flag("BAD", "EMOD trending upward over 3 years AND no documented safety/return-to-work program -- loss history problem likely to continue", "bad")
    pdf.flag("BAD", "Split EMOD (separate primary/excess layers) not reflected in premium calculation -- ask broker to verify", "bad")
    pdf.flag("GOOD", "EMOD < 0.85 with documented safety program -- competitive advantage worth highlighting in presentation", "good")
    pdf.bullet("If EMOD is not shown: ask whether the account qualifies for experience rating (typically >$10k in premium over 3 years)")

    pdf.section("4. Employer's Liability Limits (Part Two)")
    pdf.bullet("WC Part One (statutory) has no dollar limit -- Part Two (Employer's Liability) does")
    pdf.bullet("Default limits: $100k / $500k / $100k (by occurrence / disease policy limit / disease per employee)")
    pdf.bullet("Contract minimum: many MSAs and general contracts require EL limits of $500k / $500k / $500k or $1M / $1M / $1M")
    pdf.flag("BAD", "Default $100k EL limits when the client's contracts require $500k or $1M -- noncompliant with contract requirements", "bad")
    pdf.flag("BAD", "Client has operations in states where EL limits are typically challenged (CA, NY, FL) and limits are at the default -- consider limit adequacy", "bad")
    pdf.bullet("EL sits under the umbrella/excess policy -- confirm the umbrella lists WC as an underlying policy and that EL limits meet the umbrella's underlying required minimums")

    pdf.add_page()
    pdf.section("5. Waiver of Subrogation Endorsement")
    pdf.bullet("Many MSAs and construction contracts require the insured to waive WC subrogation in favor of the general contractor or owner")
    pdf.bullet("WOS on WC = WC 00 03 13 (NCCI) or state-specific equivalent")
    pdf.bullet("Blanket WOS endorsement covers all parties required by contract -- best option for companies with multiple GCs/owners")
    pdf.flag("BAD", "Contract requires WOS on WC; policy has no WOS endorsement -- if WC carrier pays a claim and sues the GC, GC can look to the insured for breach of contract", "bad")
    pdf.flag("GOOD", "Blanket WOS endorsement on WC -- covers all parties as required by written contract, no scheduled individual naming required", "good")
    pdf.bullet("Monopolistic state WC: WOS must be obtained from the state fund -- private policy WOS does not extend to monopolistic state operations")

    pdf.section("6. Cancellation Notice Periods")
    pdf.bullet("Standard cancellation for nonpayment: 10-day notice")
    pdf.bullet("Standard cancellation for other reasons: 30-day notice")
    pdf.bullet("Many contracts (especially government and general contractor subcontracts) require 30-day notice for ANY cancellation")
    pdf.flag("BAD", "Contract requires 30-day cancellation notice; policy only provides 10 days for nonpayment -- technical noncompliance", "bad")
    pdf.bullet("Some carriers offer extended cancellation notice endorsements (30/30 or 60/60) -- worth adding if contracts require it")
    pdf.bullet("Certificate language: confirm the COI reflects the correct notice period matching the contract requirement")

    pdf.section("7. Named Insured Accuracy")
    pdf.bullet("Verify that the Named Insured exactly matches the legal entity name(s) that employ the workers")
    pdf.bullet("Common gap: operating company employees but only the holding company is named -- operating co employees may not be covered")
    pdf.bullet("Joint ventures, LLCs, and DBAs: verify whether they need to be separately listed")
    pdf.flag("UGLY", "Material operating entity or subsidiary with employees is NOT listed as Named Insured or Covered Entity -- employees of that entity have no WC coverage", "ugly")
    pdf.flag("BAD", "Entity name on policy differs from entity name on employment agreements or payroll records -- creates ambiguity at claim time", "bad")
    pdf.bullet("Professional Employer Organizations (PEOs): if client uses a PEO, WC may run through the PEO's master policy -- verify coverage applies and that the client is listed")

    pdf.section("What NOT to Flag on WC")
    pdf.note(
        "The following are commonly over-flagged on WC audits and should be handled carefully:\n"
        "- Classification code phraseology that doesn't match the job description (verify the CODE, not just the label)\n"
        "- Surplus lines placement for specialty risks (many WC excess/large deductible programs are E&S)\n"
        "- Experience modification that's slightly above 1.00 on a new account (single bad year can cause this)\n"
        "- TRIA terrorism coverage (required by statute, always included -- don't flag as a finding)\n"
        "These are informational notes at most, not Bad or Ugly findings."
    )

    out = KB / "workers-comp" / "01_WC-fast-scan-cheat-sheet.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out))
    print(f"  Created: {out}")


# ── Main ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Generating cheat-sheet PDFs...")
    make_cyber()
    make_do()
    make_epli()
    make_eo()
    make_wc()
    print("\nAll done.")
