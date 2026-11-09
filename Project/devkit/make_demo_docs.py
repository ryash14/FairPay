"""Write Kestrel's sixteen company documents as real PDFs into data/docs/.

Only needed when the capstone's pre-loaded documents are not available. Every
document opens with KESTREL HOSPITALITY GROUP, its title, one header line of a
fixed form, and sections numbered from 1. The five pay schedules are written
from one template, exactly as the SRS describes, so a corpus-wide search
really can return the wrong classification's rate.
"""
import argparse
import os
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, PROJECT)
sys.path.insert(0, HERE)

from config import config  # noqa: E402
from company_truth import RATE_WINDOWS, MOVES_ONTO, COMMITMENT_PAYMENTS  # noqa: E402

BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=6)
HEAD = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=12, leading=16, spaceBefore=8, spaceAfter=4)
TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=4)
ORG = ParagraphStyle("org", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor="#555555")
META = ParagraphStyle("meta", fontName="Helvetica", fontSize=8, leading=11, textColor="#555555", spaceAfter=10)
FULL = {"Jan": "January", "Feb": "February", "Mar": "March", "Apr": "April", "May": "May", "Jun": "June",
        "Jul": "July", "Aug": "August", "Sep": "September", "Oct": "October", "Nov": "November", "Dec": "December"}


def write_pdf(path, title, code, owner, sections):
    story = [Paragraph("KESTREL HOSPITALITY GROUP", ORG), Paragraph(title, TITLE),
             Paragraph(f"Document KHG-{code} | Version 3.2 | Owner: {owner} | Issued 01 Jul", META)]
    for number, (heading, paragraphs) in enumerate(sections, start=1):
        story.append(Paragraph(f"{number}. {heading}", HEAD))
        for text in paragraphs:
            story.append(Paragraph(text.replace("&", "&amp;"), BODY))
        story.append(Spacer(1, 2 * mm))
    SimpleDocTemplate(path, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                      bottomMargin=18 * mm, title=title, author="Kestrel Hospitality Group").build(story)


def rate_sentence(window):
    day, month = window[0].split()
    if len(window) == 4:
        return (f"From {day} {FULL[month]} the day rate is ${window[1]} per hour, the night rate is ${window[2]} per hour "
                f"and the site allowance is ${window[3]} per day.")
    return f"From {day} {FULL[month]} the ordinary rate is ${window[1]} per hour and the site allowance is ${window[2]} per day."


COVERS = {
    "Front of House": "reception, concierge, restaurant floor and bar staff who have completed any traineeship",
    "Front of House Trainee": "employees learning front of house work under a registered traineeship",
    "Kitchen": "cooks, kitchen hands and stewards who have completed any traineeship",
    "Kitchen Trainee": "employees learning kitchen work under a registered traineeship",
    "Night Audit": "night auditors who balance the day's accounts and cover the front desk overnight",
}


def schedule_sections(classification):
    windows = RATE_WINDOWS[classification]
    trainee = (f"When the traineeship ends, the employee moves to the {MOVES_ONTO[classification]} classification."
               if classification in MOVES_ONTO else "This classification has no traineeship.")
    night = classification == "Night Audit"
    return [
        ("Who this schedule covers", [
            f"This schedule sets the pay for the {classification} classification. It covers {COVERS[classification]}.",
            "It applies at every Kestrel venue and payroll centre: Sydney, Melbourne, Brisbane and Perth.",
        ]),
        ("How the rates work", [
            "Each rate takes effect on the day shown and stays in force until the next rate in this schedule takes effect.",
            "A rate applies only to this classification. A rate in another schedule never applies to these days.",
            ("Day hours are paid at the day rate and night hours at the night rate; the site allowance is paid for every "
             "calendar day of the pay period." if night else
             "Every hour is paid at the ordinary rate, and the site allowance is paid for every calendar day of the pay period."),
        ]),
        ("Rates for this financial year", [rate_sentence(w) for w in windows]),
        ("Traineeship", [trainee, ("The day a traineeship ends is recorded on the employee file. Payroll moves the employee "
                                    "onto the new classification from the next day." if classification in MOVES_ONTO else
                                    "Employees join this classification directly or after completing a traineeship.")]),
        ("Questions about this schedule", [
            "Questions about these rates go to the payroll remediation desk through the HR portal.",
        ]),
    ]


GUIDES = {
    "Rostered hours paid": ("Guide-Rostered-Hours.pdf", "Resolution Guide: Rostered Hours Paid", "RG-01", [
        "The pay period was worked out from the roster when the time clock shows the employee worked different hours.",
        "This happens most often after a clock is replaced, when a venue is short of supervisors, or when the clock export fails.",
    ], [
        "The analyst obtains the time clock export for the whole period and compares it day by day with the roster.",
        "Where no export exists, the venue manager confirms the hours in writing, or the payroll vendor audits the pay run.",
    ], [
        "Check your next payslip shows the corrected hours, and keep your own record of start and finish times.",
        "Always clock on and off yourself. If the clock is not working, tell your venue manager the same day.",
        "If anything still looks wrong, raise it again through the HR portal or with your venue manager.",
    ]),
    "Wrong classification applied": ("Guide-Wrong-Classification.pdf", "Resolution Guide: Wrong Classification Applied", "RG-02", [
        "The employee was paid on a classification other than the one they were entitled to, often after a promotion or role change.",
    ], [
        "The analyst checks the employment contract, the letter of offer and any agreed change of classification.",
        "The pay owed is worked out again on the entitled classification using that classification's own pay schedule.",
    ], [
        "Keep your letter of offer and any letter confirming a new classification.",
        "Check that your payslip shows your classification correctly from now on.",
        "If your duties change again, ask your venue manager to confirm your classification in writing.",
    ]),
    "Rate change date": ("Guide-Rate-Change-Date.pdf", "Resolution Guide: Rate Change Date", "RG-03", [
        "A new rate in the pay schedule was applied from the wrong day, usually late, so part of the period was paid at the old rate.",
    ], [
        "The analyst reads the date the rate took effect from the classification's own pay schedule and splits the period there.",
    ], [
        "Check your next payslip shows the current rate.",
        "Published rates and the days they take effect are in your classification's pay schedule on the HR portal.",
        "If a later payslip still shows the old rate, raise it through the HR portal.",
    ]),
    "Traineeship overrun": ("Guide-Traineeship-Overrun.pdf", "Resolution Guide: Traineeship Overrun", "RG-04", [
        "The employee kept being paid the trainee rate after their traineeship ended.",
    ], [
        "The analyst confirms the traineeship's last day from the employee file and the training provider.",
        "From the next day the employee is owed the classification the trainee schedule names.",
    ], [
        "Keep your traineeship completion certificate and give a copy to your venue manager.",
        "Check your payslip shows your new classification from the day after your traineeship ended.",
        "If it does not, raise it through the HR portal with a copy of your certificate.",
    ]),
    "Crossed timesheets": ("Guide-Crossed-Timesheets.pdf", "Resolution Guide: Crossed Timesheets", "RG-05", [
        "Two employees' hours were recorded against each other, usually because badges were swapped at the time clock.",
    ], [
        "The analyst compares both employees' clock records, rosters and venue sign-in sheets, and corrects both records.",
    ], [
        "Use only your own badge, and tell your venue manager straight away if your badge is lost or swapped.",
        "Check your next payslip shows only the shifts you worked.",
        "If you notice a shift you did not work, raise it through the HR portal.",
    ]),
    "Faulty timesheet": ("Guide-Faulty-Timesheet.pdf", "Resolution Guide: Faulty Timesheet", "RG-06", [
        "A manual timesheet was keyed incorrectly, a day was missed, or hours were doubled.",
    ], [
        "The analyst compares the timesheet with the roster, the clock where one exists, and the supervisor's confirmation.",
    ], [
        "Check your timesheet before you sign it, and keep a copy.",
        "Tell your supervisor about any mistake before the pay run closes.",
        "If a reported error is not fixed, raise it through the HR portal.",
    ]),
    "Venue transfer hours": ("Guide-Venue-Transfer.pdf", "Resolution Guide: Venue Transfer Hours", "RG-07", [
        "Hours were lost when the employee moved between venues inside a pay period.",
    ], [
        "The analyst collects the hours from both venues' clock records and confirms the transfer date.",
    ], [
        "When you move venue, check that your first payslip includes shifts from both venues.",
        "Ask your new venue manager to confirm your start date in writing.",
        "If shifts are missing, raise it through the HR portal.",
    ]),
    "Deductions and tax": ("Guide-Deductions-And-Tax.pdf", "Resolution Guide: Deductions and Tax", "RG-08", [
        "The employee is surprised by a tax change, a salary packaging deduction or another deduction, and the gross pay is right.",
    ], [
        "The analyst confirms the gross pay is correct and explains each deduction on the payslip.",
    ], [
        "Read the deductions section of your payslip; each deduction is listed with its reason.",
        "Salary packaging changes can be reviewed on the HR portal.",
        "For personal tax advice, speak to a registered tax agent.",
    ]),
}


def guide_sections(about, confirm, steps):
    return [
        ("What this query looks like", about),
        ("How the desk confirms it", confirm),
        ("How the pay is put right", [
            "The pay owed is worked out again from the verified hours on the classification owed, piece by piece, and rounded once.",
            "Pay is corrected only when the difference is AUD 1.00 or more, whether the employee was underpaid or overpaid.",
            "Each piece of the period is paid at the rates of the classification owed on those days, read from that "
            "classification's own pay schedule, together with its site allowance for every calendar day.",
            "The verified hours are shared across the pieces in proportion to their days, because the records say how much "
            "was worked rather than on which day.",
            "The analyst then compares the pay owed with the amount paid and records the difference, its direction and "
            "whether a payroll commitment was broken.",
        ]),
        ("Steps for the employee", steps),
    ]


POLICY = [
    ("Purpose", ["This policy sets out how Kestrel handles an employee's pay query, from the first contact to the correction."]),
    ("Roles", [
        "A Payroll Analyst investigates a pay query and opens its assessment.",
        "A Remediation Controller approves or refuses a pay correction.",
        "An HR Service Desk Agent takes calls and messages from employees and tells them where their query has got to.",
    ]),
    ("Who decides", [
        "Investigating a query and approving its correction are kept apart.",
        "The person who opened an assessment may not decide it; another Remediation Controller decides.",
    ]),
    ("The financial year", ["Kestrel pays by the financial year, from 1 July to 30 June. Every pay period falls inside one financial year."]),
    ("How the pay owed is worked out", [
        "The pay owed is worked out from the hours the investigation verified, never from the payslip.",
        "The period is split wherever the classification owed or its rate changes. The hours are shared across the pieces by days.",
        "Each piece is paid at its own rates with its site allowance, and the pieces are added and rounded once to the cent.",
    ]),
    ("The three outcomes", [
        "Uphold pay: the pay stands and nothing is paid.",
        "Correct pay: a pay correction statement is issued for the difference.",
        ("Correct and compensate: the pay is corrected and the employee is also written to with an apology and the Payroll "
         "Commitments payment, which is due only where a commitment was broken."),
        "Pay is corrected only when the difference is AUD 1.00 or more, whether the employee was underpaid or overpaid.",
    ]),
    ("The pay correction statement", [
        "The statement is the only place the employee is given the corrected pay's figures.",
        "It shows every piece of the period once, in date order, the pay owed, the amount paid and the settled amount.",
    ]),
    ("The remediation letter", [
        "The letter uses plain words and short sentences and makes one apology.",
        "It names any commitment payment and says a pay correction statement follows separately.",
        "It directs the employee to the HR portal or their venue manager and gives no internal detail.",
    ]),
    ("What the service desk may say", [
        "An HR Service Desk Agent may tell an employee a query's status and when it last changed.",
        "The service desk never quotes an amount; any amount is given to the employee in writing.",
    ]),
    ("Effort", [
        "Each query is estimated in analyst hours. A query estimated at more than six hours is worked by a senior payroll officer.",
        "Where an employee needs an interpreter, the estimate is increased once to allow for it.",
    ]),
    ("Records", ["Every assessment, decision and document is kept for audit for seven years."]),
]


def commitments_sections():
    phrases = config.COMMITMENT_BREACH_PHRASES
    return [
        ("Our payroll commitments", [
            "Kestrel makes three commitments about pay. When a record shows one was broken, Kestrel pays the employee a fixed amount.",
            "Commitment payments are paid only together with a pay correction, whether the employee was underpaid or overpaid.",
        ]),
        ("PC1: Agreed classification", ["Kestrel applies an agreed classification from the day it is agreed.",
                                        f"When {phrases['PC1']}, Kestrel pays the employee ${COMMITMENT_PAYMENTS['PC1']}."]),
        ("PC2: Clocked hours", ["Kestrel pays from the time clock wherever a venue has one.",
                                f"When {phrases['PC2']}, Kestrel pays the employee ${COMMITMENT_PAYMENTS['PC2']}."]),
        ("PC3: Timesheet errors", ["Kestrel investigates every timesheet error an employee reports.",
                                   f"When {phrases['PC3']}, Kestrel pays the employee ${COMMITMENT_PAYMENTS['PC3']}."]),
        ("More than one commitment", ["Where more than one commitment was broken, every payment due is added together."]),
    ]


CASEBOOK = [
    ("About this casebook", ["Closed queries kept for training analysts. Names and identifiers have been removed."]),
    ("Case A: roster paid after a clock replacement", [
        "A Brisbane kitchen hand was paid from the roster for six fortnights while the clock was replaced. The verified hours were "
        "higher and the pay was corrected with the PC2 payment."]),
    ("Case B: trainee rate after completion", [
        "A Melbourne front of house trainee finished in March and stayed on the trainee rate until May. The period was split at "
        "the hand-over day and corrected."]),
    ("Case C: crossed badges", ["Two Sydney attendants swapped badges for a fortnight. Both records were corrected."]),
    ("Case D: tax surprise", ["A Perth night auditor queried a lower net pay. The gross pay was right and the pay was upheld."]),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    arguments = parser.parse_args()
    os.chdir(PROJECT)
    os.makedirs(config.DOCS_DIRECTORY, exist_ok=True)
    existing = [f for f in os.listdir(config.DOCS_DIRECTORY) if f.lower().endswith(".pdf")]
    if len(existing) >= 16 and not arguments.force:
        print("documents already present; use --force to rebuild")
        return
    codes = {"Front of House": "PS-01", "Front of House Trainee": "PS-02", "Kitchen": "PS-03",
             "Kitchen Trainee": "PS-04", "Night Audit": "PS-05"}
    for classification, document in config.SCHEDULE_DOCUMENT_BY_CLASSIFICATION.items():
        write_pdf(os.path.join(config.DOCS_DIRECTORY, document), f"Pay Schedule: {classification}", codes[classification],
                  "Payroll Office", schedule_sections(classification))
    write_pdf(os.path.join(config.DOCS_DIRECTORY, config.COMMITMENTS_DOCUMENT), "Payroll Commitments", "PC-01",
              "Payroll Office", commitments_sections())
    write_pdf(os.path.join(config.DOCS_DIRECTORY, "Pay-Query-Policy.pdf"), "Pay Query Policy", "POL-01",
              "People and Culture", POLICY)
    for category, (file_name, title, code, about, confirm, steps) in GUIDES.items():
        write_pdf(os.path.join(config.DOCS_DIRECTORY, file_name), title, code, "Payroll Remediation",
                  guide_sections(about, confirm, steps))
    write_pdf(os.path.join(config.DOCS_DIRECTORY, "Past-Queries-Casebook.pdf"), "Past Queries Casebook", "CB-01",
              "Payroll Remediation", CASEBOOK)
    print(f"wrote {len(os.listdir(config.DOCS_DIRECTORY))} documents to {config.DOCS_DIRECTORY}")


if __name__ == "__main__":
    main()
