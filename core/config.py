"""Central configuration: paths, colors, weights, thresholds."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIT_DB_PATH = PROJECT_ROOT / "audit" / "audit_trail.db"
OBSERVABILITY_DB_PATH = PROJECT_ROOT / "observability" / "observability.db"

CSV_PATHS = {
    "customers": PROJECT_ROOT / "customers.csv",
    "accounts": PROJECT_ROOT / "accounts.csv",
    "transactions": PROJECT_ROOT / "transactions.csv",
    "incidents": PROJECT_ROOT / "incidents.csv",
    "api_logs": PROJECT_ROOT / "api_logs.csv",
    "application_logs": PROJECT_ROOT / "application_logs.csv",
    "test_cases": PROJECT_ROOT / "test_cases.csv",
    "reference_data": PROJECT_ROOT / "reference_data.csv",
}

# ---- Theme colors (dark blue enterprise) ----
COLOR_NAVY = "#0a1e3f"
COLOR_NAVY_LIGHT = "#16326b"
COLOR_BG = "#0b1220"
COLOR_PANEL = "#132339"
COLOR_TEXT = "#e8eef7"
COLOR_ACCENT = "#3b82f6"

RISK_BUCKET_COLORS = {
    "Low": "#22c55e",
    "Medium": "#eab308",
    "High": "#f97316",
    "Critical": "#ef4444",
}

# ---- Risk scoring weights (sum to 100) ----
RISK_WEIGHTS = {
    "kyc": 20,
    "account": 20,
    "amount": 15,
    "behavioral": 15,
    "fraud_signals": 15,
    "governance": 15,
}

RISK_BUCKETS = [
    (0, 30, "Low"),
    (31, 60, "Medium"),
    (61, 80, "High"),
    (81, 100, "Critical"),
]

HIGH_RISK_BUCKETS = {"High", "Critical"}

# High-value transaction threshold referenced in CLAUDE.md worked example (₹9,50,000)
HIGH_VALUE_TXN_THRESHOLD_INR = 500_000

ALLOWED_CURRENCIES = {"INR", "USD", "GBP", "EUR", "AED", "SGD", "JPY", "AUD", "CAD"}

# PII columns masked before any on-screen display
PII_COLUMNS = {
    "customer_name",
    "ip_address",
    "device_id",
    "annual_income_inr",
    "occupation",
}

DATA_RETENTION_DAYS = 400
