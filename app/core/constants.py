class AlertStatus:
    NEW       = "NEW"
    TRIAGED   = "TRIAGED"
    ESCALATED = "ESCALATED"
    CLOSED    = "CLOSED"
    PROCESSED = "PROCESSED"

CLASSIFICATIONS = [
    "Credential Phishing",
    "Business Email Compromise",
    "Malware Delivery",
    "Spam",
    "Benign",
    "Unknown",
]

SEVERITIES = ["Critical", "High", "Medium", "Low"]

SEVERITY_COLOR = {
    "Critical": "danger",
    "High":     "warning",
    "Medium":   "info",
    "Low":      "secondary",
}

STATUS_COLOR = {
    "NEW":       "primary",
    "PROCESSED": "secondary",
    "TRIAGED":   "info",
    "ESCALATED": "warning",
    "CLOSED":    "success",
}
