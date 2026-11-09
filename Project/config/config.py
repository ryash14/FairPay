"""FairPay AI configuration (devkit reference copy).

The capstone environment ships its own complete ``config/config.py``. This file
is a faithful stand-in written from the SRS so the project can be run
end to end outside that environment (``python devkit/bootstrap_demo.py``).
If your Project folder already has the pre-loaded config.py, keep that one.

No rate, rate date, traineeship move or commitment payment lives here: those
are read from the PDFs at run time.
"""
from decimal import Decimal
import os

# ---------------------------------------------------------------- paths
PROJECT_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _path(*parts):
    return os.path.join(*parts)


DATA_DIRECTORY = "data"
DOCS_DIRECTORY = _path("data", "docs")
RAW_QUERIES_TRAIN_FILE = _path("data", "pay_queries_train.csv")
RAW_QUERIES_EVAL_FILE = _path("data", "pay_queries_eval.csv")
RAW_EFFORT_TRAIN_FILE = _path("data", "remediation_effort_train.csv")
RAW_EFFORT_EVAL_FILE = _path("data", "remediation_effort_eval.csv")
RAW_QUERY_NOTES_FILE = _path("data", "employee_query_notes.csv")
OPEN_QUERIES_FILE = _path("data", "input", "open_pay_queries.csv")
OPEN_QUERY_NOTES_FILE = _path("data", "input", "open_query_notes.csv")

PROCESSED_DIRECTORY = "processed"
CLEAN_QUERIES_TRAIN_FILE = _path("processed", "pay_queries_train_clean.csv")
CLEAN_QUERIES_EVAL_FILE = _path("processed", "pay_queries_eval_clean.csv")
CLEAN_EFFORT_TRAIN_FILE = _path("processed", "remediation_effort_train_clean.csv")
CLEAN_EFFORT_EVAL_FILE = _path("processed", "remediation_effort_eval_clean.csv")
CLEAN_QUERY_NOTES_FILE = _path("processed", "employee_query_notes_clean.csv")

OUTPUT_DIRECTORY = "output"
MODEL_DIRECTORY = _path("output", "models")
DATA_QUALITY_REPORT_FILE = _path("output", "data_quality_report.json")
MODEL_METRICS_FILE = _path("output", "model_metrics.json")
CORRECTION_MODEL_FILE = _path("output", "models", "correction_model.pkl")
EFFORT_MODEL_FILE = _path("output", "models", "effort_model.pkl")
CATEGORY_MODEL_FILE = _path("output", "models", "category_model.pkl")
CORRECTION_SCHEMA_FILE = _path("output", "models", "correction_features.json")
EFFORT_SCHEMA_FILE = _path("output", "models", "effort_features.json")

DATABASE_DIRECTORY = "database"
APPLICATION_DATABASE_FILE = _path("database", "fairpay.db")
APPLICATION_DATABASE_URL = "sqlite:///" + APPLICATION_DATABASE_FILE
CHECKPOINT_DATABASE_FILE = _path("database", "checkpoint.db")
VECTOR_STORE_DIRECTORY = _path("database", "chroma_store")
VECTOR_COLLECTION_NAME = "fairpay_documents"

# ---------------------------------------------------------------- organisation
ORGANISATION_NAME = "Kestrel Hospitality Group"
RANDOM_SEED = 42

# ---------------------------------------------------------------- financial year
FINANCIAL_YEAR_MONTHS = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
                         "Jan", "Feb", "Mar", "Apr", "May", "Jun"]
FINANCIAL_YEAR_MONTH_LENGTHS = {"Jul": 31, "Aug": 31, "Sep": 30, "Oct": 31, "Nov": 30, "Dec": 31,
                                "Jan": 31, "Feb": 28, "Mar": 31, "Apr": 30, "May": 31, "Jun": 30}
FINANCIAL_YEAR_DATES = [f"{day:02d} {month}" for month in FINANCIAL_YEAR_MONTHS
                        for day in range(1, FINANCIAL_YEAR_MONTH_LENGTHS[month] + 1)]
DAY_NUMBER_BY_FINANCIAL_YEAR_DATE = {date: number for number, date in enumerate(FINANCIAL_YEAR_DATES, start=1)}
FINANCIAL_YEAR_DATE_BY_DAY_NUMBER = {number: date for date, number in DAY_NUMBER_BY_FINANCIAL_YEAR_DATE.items()}
MONTH_BY_NUMBER = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                   7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
MONTH_NAME_MAPPING = {
    "january": "Jan", "jan": "Jan", "february": "Feb", "feb": "Feb", "march": "Mar", "mar": "Mar",
    "april": "Apr", "apr": "Apr", "may": "May", "june": "Jun", "jun": "Jun", "july": "Jul", "jul": "Jul",
    "august": "Aug", "aug": "Aug", "september": "Sep", "sept": "Sep", "sep": "Sep",
    "october": "Oct", "oct": "Oct", "november": "Nov", "nov": "Nov", "december": "Dec", "dec": "Dec",
}

# ---------------------------------------------------------------- null & booleans
NULL_TOKENS = ["", "-", "n/a", "none", "?", "not recorded"]
BOOLEAN_YES = "Yes"
BOOLEAN_NO = "No"
BOOLEAN_MAPPING = {"y": "Yes", "yes": "Yes", "true": "Yes", "1": "Yes",
                   "n": "No", "no": "No", "false": "No", "0": "No"}
BOOLEAN_LABELS = {"Yes": "yes", "No": "no"}

# ---------------------------------------------------------------- columns
QUERY_REFERENCE_COLUMN = "query_reference"
QUERY_REFERENCE_PATTERN = r"PQR-(?:SYD|MEL|BNE|PER)-\d{7}"
PAYROLL_CENTRE_COLUMN = "payroll_centre"
PAYROLL_SYSTEM_COLUMN = "payroll_system"
PERIOD_START_COLUMN = "period_start_date"
PERIOD_END_COLUMN = "period_end_date"
DAYS_IN_PERIOD_COLUMN = "days_in_period"
PAID_CLASSIFICATION_COLUMN = "paid_classification"
ENTITLED_CLASSIFICATION_COLUMN = "entitled_classification"
TRAINEESHIP_LAST_DAY_COLUMN = "traineeship_last_day"
ROSTER_TYPE_COLUMN = "roster_type"
ORDINARY_HOURS_COLUMN = "ordinary_hours_paid"
NIGHT_HOURS_COLUMN = "night_hours_paid"
TOTAL_HOURS_COLUMN = "total_hours_paid"
AMOUNT_PAID_COLUMN = "amount_paid_aud"
CONTRACTED_HOURS_COLUMN = "contracted_hours_per_week"
INTERPRETER_COLUMN = "interpreter_required_flag"
QUERY_TARGET_COLUMN = "pay_corrected"
QUERY_TARGET_ENCODING = {"Yes": 1, "No": 0}
VERIFIED_HOURS_SOURCE_COLUMN = "verified_hours_source"
VERIFIED_ORDINARY_HOURS_COLUMN = "verified_ordinary_hours"
VERIFIED_NIGHT_HOURS_COLUMN = "verified_night_hours"
EFFORT_TARGET_COLUMN = "remediation_hours"
NOTE_SEQUENCE_COLUMN = "note_sequence"
NOTE_TIMESTAMP_COLUMN = "note_written_at"
NOTE_TEXT_COLUMN = "note_text"
NOTE_LENGTH_COLUMN = "note_length_chars"
NOTE_TARGET_COLUMN = "query_category"
NOTE_DATE_PART = "note_written_date"
NOTE_TIME_PART = "note_written_time"

STANDARD_ROSTER_TYPE = "Standard"
DAY_NIGHT_ROSTER_TYPE = "Day-night"

VERIFIED_HOURS_SOURCES = ["Time clock export", "Venue manager confirmation", "Payroll vendor audit"]
MANAGER_INTERVIEW_HOURS_SOURCES = ["Venue manager confirmation"]
VENDOR_AUDIT_HOURS_SOURCES = ["Payroll vendor audit"]
VENUE_MANAGER_HOURS_SOURCES = ["Venue manager confirmation"]

COMMITMENT_BREACH_COLUMNS = {
    "PC1": "agreed_classification_not_applied_flag",
    "PC2": "rostered_without_clock_check_flag",
    "PC3": "timesheet_error_not_investigated_flag",
}
COMMITMENT_BREACH_PHRASES = {
    "PC1": "an agreed classification is not applied",
    "PC2": "hours are paid from the roster without a time clock check",
    "PC3": "a reported timesheet error is not investigated",
}

# ---------------------------------------------------------------- classifications & documents
SCHEDULE_DOCUMENT_BY_CLASSIFICATION = {
    "Front of House": "Pay-Schedule-Front-Of-House.pdf",
    "Front of House Trainee": "Pay-Schedule-Front-Of-House-Trainee.pdf",
    "Kitchen": "Pay-Schedule-Kitchen.pdf",
    "Kitchen Trainee": "Pay-Schedule-Kitchen-Trainee.pdf",
    "Night Audit": "Pay-Schedule-Night-Audit.pdf",
}
COMMITMENTS_DOCUMENT = "Payroll-Commitments.pdf"
POLICY_DOCUMENT = "Pay-Query-Policy.pdf"
CASEBOOK_DOCUMENT = "Past-Queries-Casebook.pdf"
QUERY_CATEGORIES = [
    "Crossed timesheets",
    "Deductions and tax",
    "Faulty timesheet",
    "Rate change date",
    "Rostered hours paid",
    "Traineeship overrun",
    "Venue transfer hours",
    "Wrong classification applied",
]
GUIDE_DOCUMENT_BY_CATEGORY = {
    "Crossed timesheets": "Guide-Crossed-Timesheets.pdf",
    "Deductions and tax": "Guide-Deductions-And-Tax.pdf",
    "Faulty timesheet": "Guide-Faulty-Timesheet.pdf",
    "Rate change date": "Guide-Rate-Change-Date.pdf",
    "Rostered hours paid": "Guide-Rostered-Hours.pdf",
    "Traineeship overrun": "Guide-Traineeship-Overrun.pdf",
    "Venue transfer hours": "Guide-Venue-Transfer.pdf",
    "Wrong classification applied": "Guide-Wrong-Classification.pdf",
}
CHAT_EXCLUDED_DOCUMENTS = [CASEBOOK_DOCUMENT]

# ---------------------------------------------------------------- value mappings
PAYROLL_CENTRE_MAPPING = {
    "sydney": "Sydney", "syd": "Sydney", "sydney cbd": "Sydney",
    "melbourne": "Melbourne", "melb": "Melbourne", "mel": "Melbourne",
    "brisbane": "Brisbane", "bne": "Brisbane", "brissy": "Brisbane",
    "perth": "Perth", "per": "Perth", "perth wa": "Perth",
}
PAYROLL_SYSTEM_MAPPING = {
    "kestrel payhub": "Kestrel PayHub", "payhub": "Kestrel PayHub",
    "harbour payroll": "Harbour Payroll", "harbour": "Harbour Payroll",
    "coastline pay": "Coastline Pay", "coastline": "Coastline Pay",
    "westpay us": "WestPay US", "westpay": "WestPay US",
}
MONTH_FIRST_BY_PAYROLL_SYSTEM = {"Kestrel PayHub": False, "Harbour Payroll": False,
                                 "Coastline Pay": False, "WestPay US": True}
CONTACT_CHANNEL_MAPPING = {"email": "Email", "e-mail": "Email", "phone": "Phone", "call": "Phone",
                           "hr portal": "HR portal", "portal": "HR portal", "in person": "In person",
                           "walk-in": "In person"}
PAY_FREQUENCY_MAPPING = {"fortnightly": "Fortnightly", "fn": "Fortnightly", "monthly": "Monthly", "mth": "Monthly"}
CLASSIFICATION_MAPPING = {
    "front of house": "Front of House", "foh": "Front of House",
    "front of house trainee": "Front of House Trainee", "foh trainee": "Front of House Trainee",
    "kitchen": "Kitchen", "kit": "Kitchen",
    "kitchen trainee": "Kitchen Trainee", "kit trainee": "Kitchen Trainee",
    "night audit": "Night Audit", "night auditor": "Night Audit", "nightaudit": "Night Audit",
}
ROSTER_TYPE_MAPPING = {"standard": "Standard", "std": "Standard",
                       "day-night": "Day-night", "day night": "Day-night", "dn": "Day-night"}
HOURS_SOURCE_MAPPING = {"time clock": "Time clock", "clock": "Time clock", "timesheet": "Timesheet",
                        "manual timesheet": "Timesheet", "rostered": "Rostered", "roster": "Rostered"}
PAYMENT_METHOD_MAPPING = {"bank transfer": "Bank transfer", "eft": "Bank transfer",
                          "pay card": "Pay card", "paycard": "Pay card", "cheque": "Cheque", "chq": "Cheque"}
ANALYST_GRADE_MAPPING = {
    "associate payroll officer": "Associate Payroll Officer", "assoc. payroll officer": "Associate Payroll Officer",
    "payroll officer": "Payroll Officer", "po": "Payroll Officer",
    "senior payroll officer": "Senior Payroll Officer", "snr payroll officer": "Senior Payroll Officer",
    "team leader": "Team Leader", "tl": "Team Leader",
}
CORRECTION_BAND_MAPPING = {"high": "High", "medium": "Medium", "med": "Medium", "low": "Low"}
QUERY_CATEGORY_MAPPING = {category.lower(): category for category in QUERY_CATEGORIES}
QUERY_CATEGORY_MAPPING.update({"crossed badges": "Crossed timesheets", "tax query": "Deductions and tax",
                               "rostered hours": "Rostered hours paid", "wrong classification": "Wrong classification applied"})
NOTE_SOURCE_MAPPING = {"first contact": "First contact", "follow-up": "Follow-up", "follow up": "Follow-up",
                       "officer update": "Officer update", "callback": "Callback", "call back": "Callback",
                       "closure note": "Closure note", "closure": "Closure note"}

QUERY_FLAG_COLUMNS = ["electronic_timesheet_flag", "venue_transfer_flag", INTERPRETER_COLUMN, QUERY_TARGET_COLUMN]
EFFORT_FLAG_COLUMNS = ["electronic_timesheet_flag", "clock_records_obtained_flag", "manager_interview_required_flag",
                       "vendor_audit_required_flag", "venue_manager_involved_flag", INTERPRETER_COLUMN,
                       "complaint_escalated_flag"]

QUERY_VALUE_MAPPINGS = {
    PAYROLL_CENTRE_COLUMN: PAYROLL_CENTRE_MAPPING,
    PAYROLL_SYSTEM_COLUMN: PAYROLL_SYSTEM_MAPPING,
    "contact_channel": CONTACT_CHANNEL_MAPPING,
    "pay_frequency": PAY_FREQUENCY_MAPPING,
    PAID_CLASSIFICATION_COLUMN: CLASSIFICATION_MAPPING,
    ENTITLED_CLASSIFICATION_COLUMN: CLASSIFICATION_MAPPING,
    ROSTER_TYPE_COLUMN: ROSTER_TYPE_MAPPING,
    "hours_source_type": HOURS_SOURCE_MAPPING,
    "payment_method": PAYMENT_METHOD_MAPPING,
    **{column: BOOLEAN_MAPPING for column in QUERY_FLAG_COLUMNS},
}
EFFORT_VALUE_MAPPINGS = {
    "analyst_grade": ANALYST_GRADE_MAPPING,
    PAYROLL_CENTRE_COLUMN: PAYROLL_CENTRE_MAPPING,
    "contact_channel": CONTACT_CHANNEL_MAPPING,
    "query_category": QUERY_CATEGORY_MAPPING,
    "correction_band": CORRECTION_BAND_MAPPING,
    ROSTER_TYPE_COLUMN: ROSTER_TYPE_MAPPING,
    **{column: BOOLEAN_MAPPING for column in EFFORT_FLAG_COLUMNS},
}
NOTE_VALUE_MAPPINGS = {
    PAYROLL_CENTRE_COLUMN: PAYROLL_CENTRE_MAPPING,
    "contact_channel": CONTACT_CHANNEL_MAPPING,
    "note_source": NOTE_SOURCE_MAPPING,
    NOTE_TARGET_COLUMN: QUERY_CATEGORY_MAPPING,
}

# ---------------------------------------------------------------- column groups
QUERY_DATE_COLUMNS = [PERIOD_START_COLUMN, PERIOD_END_COLUMN, TRAINEESHIP_LAST_DAY_COLUMN]
QUERY_MONEY_COLUMNS = [AMOUNT_PAID_COLUMN, "salary_packaging_aud", "recovery_balance_aud"]
QUERY_HOURS_COLUMNS = [ORDINARY_HOURS_COLUMN, NIGHT_HOURS_COLUMN, TOTAL_HOURS_COLUMN]
QUERY_WHOLE_NUMBER_COLUMNS = [DAYS_IN_PERIOD_COLUMN, "consecutive_rostered_periods", "days_since_last_clock_match",
                              "hours_change_vs_average_pct", "classification_changes_in_period",
                              "traineeship_days_overrun", "rate_changes_in_period", "prior_queries_12m",
                              "tenure_months", CONTRACTED_HOURS_COLUMN]
QUERY_RANGE_LIMITS = {CONTRACTED_HOURS_COLUMN: (8, 60), "tenure_months": (0, 600),
                      "days_since_last_clock_match": (0, 365)}
EFFORT_DATE_COLUMNS = ["remediation_started_date"]
EFFORT_MONEY_COLUMNS = ["amount_at_stake_aud"]
EFFORT_DURATION_COLUMNS = [EFFORT_TARGET_COLUMN]
EFFORT_COUNT_WITH_UNIT_PATTERNS = {"letters_sent_count": r"^(\d+)(?: letters?)?$",
                                   "calls_made_count": r"^(\d+)(?: calls?)?$"}
EFFORT_WHOLE_NUMBER_COLUMNS = ["period_pieces_count", "classifications_involved_count", "analyst_open_queries_count"]
EFFORT_RANGE_LIMITS = {EFFORT_TARGET_COLUMN: (0.25, 40.0), "letters_sent_count": (0, 20),
                       "calls_made_count": (0, 30), "analyst_open_queries_count": (0, 80)}

# ---------------------------------------------------------------- notation patterns
NUMERIC_DATE_PATTERN = r"^(\d{1,2})/(\d{1,2})$"
WORDED_DATE_PATTERN = r"^(\d{1,2})[ -]([a-z]+)$"
STANDARD_DATE_PATTERN = r"^\d{2} [A-Z][a-z]{2}$"
AMOUNT_PATTERN = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
MONEY_NOTATION_PATTERN = (rf"^(?:-?{AMOUNT_PATTERN}|\${AMOUNT_PATTERN}|\$?{AMOUNT_PATTERN} aud|aud \$?{AMOUNT_PATTERN}"
                          rf"|\$?{AMOUNT_PATTERN} cr|\(\$?{AMOUNT_PATTERN}\))$")
MONEY_SYMBOL_PATTERN = r"\$|aud|cr|[(),\s]"
CREDIT_NOTATION_PATTERN = r" cr$|^\(.*\)$"
DIGIT_GROUPING_SEPARATOR = ","
HOURS_WORKED_PATTERN = rf"^({AMOUNT_PATTERN})(?: (hrs|h|min))?$"
HOURS_UNIT_FACTORS = {"h": 1.0, "hrs": 1.0, "min": 1.0 / 60.0}
UNIT_CONVERSION_DECIMALS = 4
QUARTER_HOURS_PER_HOUR = 4
HOURS_AND_MINUTES_PATTERN = r"^(\d+)\s?h\s?(\d+)\s?m$"
MINUTES_UNIT_PATTERN = r"^(\d+(?:\.\d+)?)\s?min$"
HOURS_UNIT_PATTERN = r"^(\d+(?:\.\d+)?)\s?(?:h|hrs|hours)$"
PLAIN_NUMBER_PATTERN = r"^-?\d+(?:\.\d+)?$"
MINUTES_PER_HOUR = 60
MARKUP_PATTERN = r"<[^>]+>"
ENCODING_ARTIFACT_PATTERN = r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);|\u00a0"
NO_BREAK_SPACE = "\u00a0"
WHITESPACE_RUN_PATTERN = r"\s+"
MINIMUM_NOTE_WORDS = 4
TIMESTAMP_PARTS_PATTERN = r"^(.*?)\s+(\d{1,2}):(\d{2})$"
STANDARD_TIMESTAMP_PATTERN = r"^\d{2} [A-Z][a-z]{2} \d{2}:\d{2}$"

# ---------------------------------------------------------------- document patterns
DOCUMENT_HEADER_PATTERN = r"Document KHG-[A-Z]{2,4}-\d{2} \| Version \d+\.\d+ \| Owner: [A-Za-z ]+? \| Issued \d{2} [A-Z][a-z]{2}"
SECTION_HEADING_PATTERN = r"(?m)^\s*(\d+)\. [A-Z][^\n]*$"
CONTROL_CHARACTER_PATTERN = r"[\x00-\x08\x0b-\x1f\x7f]"
SENTENCE_BOUNDARY_PATTERN = r"(?<=[.:;])(?<!\d\.)\s+"
CHUNK_SIZE_CHARACTERS = 500
CHUNK_OVERLAP_CHARACTERS = 120
SINGLE_RATE_PATTERN = (r"From (\d{1,2}) ([A-Za-z]+) the ordinary rate is \$(\d+\.\d{2}) per hour "
                       r"and the site allowance is \$(\d+\.\d{2}) per day\.")
DAY_NIGHT_RATE_PATTERN = (r"From (\d{1,2}) ([A-Za-z]+) the day rate is \$(\d+\.\d{2}) per hour, the night rate is "
                          r"\$(\d+\.\d{2}) per hour and the site allowance is \$(\d+\.\d{2}) per day\.")
MOVES_ONTO_PATTERN = r"When the traineeship ends, the employee moves to the ([A-Za-z ]+?) classification\."
NO_TRAINEESHIP_PATTERN = r"This classification has no traineeship\."
COMMITMENT_PAYMENT_PATTERN = r"When ([a-z ]+?), Kestrel pays the employee \$(\d+\.\d{2})\."

# ---------------------------------------------------------------- embeddings & retrieval
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DEVICE = "cpu"
EMPLOYEE_STEPS_QUESTION = "What steps should the employee take next?"
EMPLOYEE_STEPS_RESULT_COUNT = 2
CHAT_RETRIEVAL_RESULT_COUNT = 4
CHAT_MAX_RELEVANCE_DISTANCE = 0.62
CHAT_HISTORY_TURN_LIMIT = 3
CHAT_PAGE_TURN_LIMIT = 20
CHAT_AUDIT_MAX_ROWS = 200
CHAT_QUESTION_MINIMUM_CHARACTERS = 8

# ---------------------------------------------------------------- money & pay
CENT = Decimal("0.01")
CENTS_PER_DOLLAR = 100
PIECE_DISPLAY_QUANTUM = Decimal("0.01")
HOURS_IN_A_DAY = 24
CORRECTION_THRESHOLD_AUD = Decimal("1.00")
UNDERPAID = "Underpaid"
OVERPAID = "Overpaid"
PAID_CORRECTLY = "Paid correctly"
SETTLEMENT_PAID_TO_EMPLOYEE = "Paid to employee"
SETTLEMENT_RECOVERED = "Recovered from employee"
SETTLEMENT_NOTHING_DUE = "Nothing due"
QUEUE_DIRECTION_ALL = "All"
QUEUE_DIRECTION_OPTIONS = [QUEUE_DIRECTION_ALL, UNDERPAID, OVERPAID, PAID_CORRECTLY]

# ---------------------------------------------------------------- models
CORRECTION_NUMERIC_FEATURES = [
    DAYS_IN_PERIOD_COLUMN, ORDINARY_HOURS_COLUMN, NIGHT_HOURS_COLUMN, TOTAL_HOURS_COLUMN, AMOUNT_PAID_COLUMN,
    "consecutive_rostered_periods", "days_since_last_clock_match", "hours_change_vs_average_pct",
    "classification_changes_in_period", "traineeship_days_overrun", "rate_changes_in_period",
    "prior_queries_12m", "tenure_months", CONTRACTED_HOURS_COLUMN, "salary_packaging_aud", "recovery_balance_aud",
]
CORRECTION_CATEGORICAL_FEATURES = [
    PAYROLL_CENTRE_COLUMN, PAYROLL_SYSTEM_COLUMN, "contact_channel", "pay_frequency", PAID_CLASSIFICATION_COLUMN,
    ENTITLED_CLASSIFICATION_COLUMN, ROSTER_TYPE_COLUMN, "electronic_timesheet_flag", "hours_source_type",
    "payment_method", "venue_transfer_flag", INTERPRETER_COLUMN,
]
EFFORT_NUMERIC_FEATURES = ["period_pieces_count", "classifications_involved_count", "amount_at_stake_aud",
                           "letters_sent_count", "calls_made_count", "analyst_open_queries_count"]
EFFORT_CATEGORICAL_FEATURES = [
    "analyst_grade", PAYROLL_CENTRE_COLUMN, "contact_channel", "query_category", "correction_band", ROSTER_TYPE_COLUMN,
    "electronic_timesheet_flag", "clock_records_obtained_flag", "manager_interview_required_flag",
    "vendor_audit_required_flag", "venue_manager_involved_flag", INTERPRETER_COLUMN, "complaint_escalated_flag",
]
NOTE_HELD_OUT_SHARE = 0.2
MINIMUM_CORRECTION_ROC_AUC = 0.78
MINIMUM_EFFORT_R2 = 0.75
MINIMUM_CATEGORY_MACRO_F1 = 0.88
PROBABILITY_DECIMALS = 4
CORRECTION_BAND_HIGH = "High"
CORRECTION_BAND_MEDIUM = "Medium"
CORRECTION_BAND_LOW = "Low"
CORRECTION_BAND_HIGH_THRESHOLD = 0.6
CORRECTION_BAND_MEDIUM_THRESHOLD = 0.3
EFFORT_PLANNING_ASSUMPTIONS = {"analyst_grade": "Payroll Officer", "letters_sent_count": 2, "calls_made_count": 2,
                               "analyst_open_queries_count": 15, "complaint_escalated_flag": "No"}
INTERPRETER_EFFORT_MULTIPLIER = 1.25
SENIOR_REVIEW_THRESHOLD_HOURS = 6.0
EFFORT_HOURS_DECIMALS = 2

# ---------------------------------------------------------------- workflow
AGENT_NAME_PLANNER = "planner"
AGENT_NAME_CORRECTION = "correction_risk_analyst"
AGENT_NAME_CATEGORY = "category_analyst"
AGENT_NAME_PAY_RATE = "pay_rate_advisor"
AGENT_NAME_WRITER = "assessment_writer"
AGENT_NAME_REMEDIATION_LETTER = "remediation_letter_writer"
AGENT_NAME_PAY_STATEMENT = "pay_statement_writer"
AGENT_NAME_PAYROLL_ASSISTANT = "payroll_assistant"
GEMINI_API_KEY_VARIABLE = "GEMINI_API_KEY"
GEMINI_MODEL_VARIABLE = "GEMINI_MODEL"
GEMINI_MAX_OUTPUT_TOKENS = 4096
GEMINI_TEMPERATURE = 0.2
RESPONSE_DECORATION_CHARACTERS = "*#-•>[]()_`: "
RUN_ID_PREFIX = "RUN-"
ASSESSMENT_ID_PREFIX = "PQA-"
IDENTIFIER_HEX_LENGTH = 10
AGENT_RUN_STATUS_RUNNING = "running"
AGENT_RUN_STATUS_AWAITING_DECISION = "awaiting decision"
AGENT_RUN_STATUS_COMPLETE = "complete"
AGENT_RUN_STATUS_FAILED = "failed"
AGENT_RUN_FINISHED_STATUSES = [AGENT_RUN_STATUS_COMPLETE, AGENT_RUN_STATUS_FAILED]
DECISION_UPHOLD_PAY = "UPHOLD PAY"
DECISION_CORRECT_PAY = "CORRECT PAY"
DECISION_CORRECT_AND_COMPENSATE = "CORRECT AND COMPENSATE"
DECISION_OPTIONS = [DECISION_UPHOLD_PAY, DECISION_CORRECT_PAY, DECISION_CORRECT_AND_COMPENSATE]
QUERY_STATUS_PENDING = "Pending decision"
QUERY_STATUS_BY_DECISION = {DECISION_UPHOLD_PAY: "Pay upheld", DECISION_CORRECT_PAY: "Pay corrected",
                            DECISION_CORRECT_AND_COMPENSATE: "Corrected and compensated"}
QUERY_STATUS_OPTIONS = [QUERY_STATUS_PENDING, *QUERY_STATUS_BY_DECISION.values()]
DECIDED_QUERY_STATUSES = list(QUERY_STATUS_BY_DECISION.values())
LLM_CALLS_BEFORE_DECISION = 5
LLM_CALLS_BY_DECISION = {DECISION_UPHOLD_PAY: 5, DECISION_CORRECT_PAY: 6, DECISION_CORRECT_AND_COMPENSATE: 7}

# ---------------------------------------------------------------- access
ROLE_CONTROLLER = "Remediation Controller"
ROLE_ANALYST = "Payroll Analyst"
ROLE_SERVICE_DESK = "HR Service Desk Agent"
AREA_INTAKE = "intake"
AREA_ASSESSMENT = "assessment"
AREA_DECISION = "decision"
AREA_AUDIT = "audit"
AREA_CHAT = "chat"
AREA_BY_PATH_START = {"/queue": AREA_INTAKE, "/assessments": AREA_ASSESSMENT, "/queries": AREA_AUDIT,
                      "/audit": AREA_AUDIT, "/chat": AREA_CHAT}
DECISION_PATH_ENDING = "/decision"
ROLE_AREA_ACCESS = {
    ROLE_CONTROLLER: [AREA_INTAKE, AREA_ASSESSMENT, AREA_DECISION, AREA_AUDIT, AREA_CHAT],
    ROLE_ANALYST: [AREA_INTAKE, AREA_ASSESSMENT, AREA_AUDIT, AREA_CHAT],
    ROLE_SERVICE_DESK: [AREA_CHAT],
}
PAGE_QUEUE = "Query queue"
PAGE_QUERY = "Query detail"
PAGE_DECISION = "Decision queue"
PAGE_AUDIT = "Audit trail"
PAGE_CHAT = "Payroll chat"
ROLE_PAGE_ACCESS = {
    ROLE_CONTROLLER: [PAGE_QUEUE, PAGE_QUERY, PAGE_DECISION, PAGE_AUDIT, PAGE_CHAT],
    ROLE_ANALYST: [PAGE_QUEUE, PAGE_QUERY, PAGE_AUDIT, PAGE_CHAT],
    ROLE_SERVICE_DESK: [PAGE_CHAT],
}
PASSWORD_HASH_ALGORITHM = "sha256"
PASSWORD_HASH_ROUNDS = 120_000
PASSWORD_SALT_BYTES = 16
SESSION_TOKEN_BYTES = 32
SESSION_TOKEN_HEADER = "X-Session-Token"
SEED_USER_ACCOUNTS = [
    {"username": "olivia", "display_name": "Olivia Brennan", "role": ROLE_CONTROLLER, "password": "Controller#2025"},
    {"username": "marcus", "display_name": "Marcus Tan", "role": ROLE_CONTROLLER, "password": "Controller#2025"},
    {"username": "priya", "display_name": "Priya Raman", "role": ROLE_CONTROLLER, "password": "Controller#2025"},
    {"username": "daniel", "display_name": "Daniel Okafor", "role": ROLE_ANALYST, "password": "Analyst#2025"},
    {"username": "sofia", "display_name": "Sofia Marchetti", "role": ROLE_ANALYST, "password": "Analyst#2025"},
    {"username": "liam", "display_name": "Liam Walsh", "role": ROLE_ANALYST, "password": "Analyst#2025"},
    {"username": "aisha", "display_name": "Aisha Karimi", "role": ROLE_ANALYST, "password": "Analyst#2025"},
    {"username": "tom", "display_name": "Tom Nguyen", "role": ROLE_ANALYST, "password": "Analyst#2025"},
    {"username": "grace", "display_name": "Grace Whitfield", "role": ROLE_ANALYST, "password": "Analyst#2025"},
    {"username": "hannah", "display_name": "Hannah Lee", "role": ROLE_SERVICE_DESK, "password": "Desk#2025"},
    {"username": "ravi", "display_name": "Ravi Menon", "role": ROLE_SERVICE_DESK, "password": "Desk#2025"},
    {"username": "chloe", "display_name": "Chloe Dubois", "role": ROLE_SERVICE_DESK, "password": "Desk#2025"},
    {"username": "jack", "display_name": "Jack O'Connell", "role": ROLE_SERVICE_DESK, "password": "Desk#2025"},
    {"username": "mei", "display_name": "Mei Chen", "role": ROLE_SERVICE_DESK, "password": "Desk#2025"},
    {"username": "omar", "display_name": "Omar Haddad", "role": ROLE_SERVICE_DESK, "password": "Desk#2025"},
]

# ---------------------------------------------------------------- service
API_TITLE = "FairPay AI API"
API_HOST = "0.0.0.0"
API_PORT = 8081
API_BASE_URL = "http://localhost:8081"
API_REQUEST_TIMEOUT_SECONDS = 300
ANALYST_REQUEST_MINIMUM_CHARACTERS = 15
DECISION_REASON_MINIMUM_CHARACTERS = 15
SIGN_IN_FAILED_MESSAGE = "That username and password do not match an account."
SIGN_IN_REQUIRED_MESSAGE = "Sign in to use FairPay AI."
AREA_REFUSED_MESSAGE = "The {role} role cannot reach the {area} area."
OWN_ASSESSMENT_REFUSED_MESSAGE = ("You opened this assessment, so another Remediation Controller must decide it. "
                                  "The Pay Query Policy separates investigating a query from approving its correction.")
QUERY_NOT_IN_QUEUE_MESSAGE = "Pay query {query_reference} is not in the open queue."
QUERY_WITHOUT_NOTES_MESSAGE = "Pay query {query_reference} has no employee notes."
ASSESSMENT_NOT_FOUND_MESSAGE = "No assessment has that identifier."
ALREADY_DECIDED_MESSAGE = "This assessment has already been decided."
DECISION_IN_PROGRESS_MESSAGE = "A decision to {decision} is already being recorded for this assessment."

# ---------------------------------------------------------------- chat
CHAT_TYPE_PAY_RATES = "PAY RATES"
CHAT_TYPE_PAYROLL_RULES = "PAYROLL RULES"
CHAT_TYPE_EMPLOYEE_ADVICE = "EMPLOYEE ADVICE"
CHAT_TYPE_QUERY_STATUS = "QUERY STATUS"
CHAT_TYPE_OUT_OF_SCOPE = "OUT OF SCOPE"
CHAT_TYPE_OPTIONS = [CHAT_TYPE_PAY_RATES, CHAT_TYPE_PAYROLL_RULES, CHAT_TYPE_EMPLOYEE_ADVICE,
                     CHAT_TYPE_QUERY_STATUS, CHAT_TYPE_OUT_OF_SCOPE]
CHAT_ANSWERED_TYPES = [CHAT_TYPE_PAY_RATES, CHAT_TYPE_PAYROLL_RULES, CHAT_TYPE_EMPLOYEE_ADVICE]
CHAT_FIGURE_ROLES = [ROLE_CONTROLLER, ROLE_ANALYST]
CHAT_REFUSAL_MESSAGE = ("I can only answer from Kestrel's pay schedules, policies, commitments and resolution guides, "
                        "and they do not cover that question.")
CHAT_UNKNOWN_QUERY_MESSAGE = "I cannot find that pay query in the open queue. Check the reference, for example PQR-SYD-0000000."
CHAT_NOT_ASSESSED_TEMPLATE = "Pay query {query_reference} is in the open queue and has not been assessed yet."
CHAT_STATUS_TEMPLATE = "Pay query {query_reference} {status_phrase}, last changed {changed_on}."
CHAT_STATUS_PHRASES = {
    QUERY_STATUS_PENDING: "has been assessed and is waiting for a Remediation Controller's decision",
    "Pay upheld": "has been decided and the pay stands",
    "Pay corrected": "has been decided and the pay is being corrected",
    "Corrected and compensated": "has been decided, the pay is being corrected and the employee is being written to",
}
CHAT_AMOUNTS_IN_WRITING_MESSAGE = "Any amounts are given to the employee in writing, never over the phone."
CHAT_STATUS_ANSWER_IN_HISTORY = "(a pay query's status was given from its record)"
STATUS_CHANGE_TIME_FORMAT = "%d %b %Y at %H:%M UTC"

# ---------------------------------------------------------------- dashboard
DASHBOARD_TITLE = "FairPay AI"
DASHBOARD_SUBTITLE = "Payroll query assessment and back-pay remediation"
NEUTRAL_BADGE_COLOUR = "gray"
DIRECTION_BADGE_COLOURS = {UNDERPAID: "red", OVERPAID: "orange", PAID_CORRECTLY: "green"}
CORRECTION_BAND_BADGE_COLOURS = {CORRECTION_BAND_HIGH: "red", CORRECTION_BAND_MEDIUM: "orange", CORRECTION_BAND_LOW: "green"}
DECISION_BADGE_COLOURS = {DECISION_UPHOLD_PAY: "gray", DECISION_CORRECT_PAY: "blue", DECISION_CORRECT_AND_COMPENSATE: "violet"}
STATUS_BADGE_COLOURS = {QUERY_STATUS_PENDING: "orange", "Pay upheld": "gray", "Pay corrected": "blue",
                        "Corrected and compensated": "violet"}
CHAT_TYPE_BADGE_COLOURS = {CHAT_TYPE_PAY_RATES: "blue", CHAT_TYPE_PAYROLL_RULES: "violet",
                           CHAT_TYPE_EMPLOYEE_ADVICE: "green", CHAT_TYPE_QUERY_STATUS: "orange",
                           CHAT_TYPE_OUT_OF_SCOPE: "gray"}
