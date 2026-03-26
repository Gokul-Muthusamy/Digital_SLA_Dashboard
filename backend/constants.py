import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "database.db"))).resolve()
TEMPLATE_DIR = PROJECT_ROOT / "frontend" / "templates"
STATIC_DIR = PROJECT_ROOT / "frontend" / "static"

WARNING_ACK_MINUTES = 15
BREACH_ACTION_MINUTES = 30
DEFAULT_ALERT_RECIPIENTS = [
    email.strip()
    for email in os.getenv("ALERT_DEFAULT_RECIPIENTS", "").split(",")
    if email.strip()
]
WARNING_THRESHOLD_PCT = 0.65
DEFAULT_SLA_EXTENSION_MINUTES = 60

MANAGER_ONLY_ACTIONS = {
    "MANAGER_REASSIGN_OWNER",
    "MANAGER_SET_PRIORITY",
    "MANAGER_SET_SLA_EXTENSION",
    "MANAGER_SLA_EXTENSION",
    "MANAGER_PREVENTIVE_INTERVENTION",
    "MANAGER_CUSTOMER_ASSURANCE",
    "MANAGER_SIGNOFF",
}

MANAGER_IMPACT_ACTIONS = MANAGER_ONLY_ACTIONS | {
    "RECOVERY_PLAN",
    "RCA_REQUIRED",
    "RCA_COMPLETED",
}

ACTION_LABELS = {
    "ACK_WARNING": "Acknowledge Warning",
    "CONTACT_CUSTOMER": "Contact Customer",
    "REPRIORITIZE": "Re-prioritize Work",
    "ESCALATE_TO_MANAGER": "Escalate to Manager",
    "RECOVERY_PLAN": "Recovery Plan Added",
    "RCA_REQUIRED": "RCA Marked Required",
    "RCA_COMPLETED": "RCA Completed",
    "CLOSE_WITH_NOTE": "Closure Note Captured",
    "CAPTURE_GOOD_PRACTICE": "Good Practice Captured",
    "MANAGER_REASSIGN_OWNER": "Manager Reassigned Owner",
    "MANAGER_SET_PRIORITY": "Manager Set Priority",
    "MANAGER_SET_SLA_EXTENSION": "Manager Set SLA Extension",
    "MANAGER_SLA_EXTENSION": "Manager Requested SLA Extension",
    "MANAGER_PREVENTIVE_INTERVENTION": "Manager Preventive Intervention",
    "MANAGER_CUSTOMER_ASSURANCE": "Manager Customer Assurance",
    "MANAGER_SIGNOFF": "Manager Sign-off",
    "EXTENSION_ACCEPTED": "User Accepted SLA Extension",
    "EXTENSION_REJECTED": "User Rejected SLA Extension",
    "EXTENSION_AUTO_APPROVED": "SLA Extension Auto-Approved",
    "RESOLVED": "Ticket Resolved",
}
