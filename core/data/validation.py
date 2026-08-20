"""Per-entity data validation rules -> structured DataQualityIssue records.

Each check function returns a boolean mask (True = violates the rule) over its
input DataFrame plus a short issue code/description. Results are aggregated
into a single issues DataFrame consumed by the Executive Overview and
Governance pages.
"""
from dataclasses import dataclass, field

import pandas as pd

from core.config import ALLOWED_CURRENCIES


@dataclass
class DataQualityIssue:
    entity: str
    issue_code: str
    description: str
    row_count: int
    entity_ids: list = field(default_factory=list)


def _issue(entity, code, desc, mask: pd.Series, id_col: str, df: pd.DataFrame) -> DataQualityIssue:
    hits = df.loc[mask]
    return DataQualityIssue(
        entity=entity,
        issue_code=code,
        description=desc,
        row_count=int(mask.sum()),
        entity_ids=hits[id_col].astype(str).tolist()[:500] if id_col in df.columns else [],
    )


def validate_customers(customers: pd.DataFrame) -> list[DataQualityIssue]:
    issues = []
    now = pd.Timestamp.now()

    future_onboard = customers["customer_since"] > now
    issues.append(_issue("customers", "FUTURE_ONBOARDING_DATE", "Future customer onboarding date",
                          future_onboard, "customer_id", customers))

    dup_customer = customers["customer_id"].duplicated(keep=False)
    issues.append(_issue("customers", "DUPLICATE_CUSTOMER_ID", "Duplicate customer_id",
                          dup_customer, "customer_id", customers))

    invalid_kyc = ~customers["kyc_status"].isin(["VERIFIED", "PENDING", "REJECTED", "EXPIRED"])
    issues.append(_issue("customers", "INVALID_KYC_STATUS", "Unrecognized KYC status value",
                          invalid_kyc, "customer_id", customers))

    invalid_status = ~customers["customer_status"].isin(["ACTIVE", "CLOSED", "SUSPENDED", "DORMANT"])
    issues.append(_issue("customers", "INVALID_CUSTOMER_STATUS", "Unrecognized customer status value",
                          invalid_status, "customer_id", customers))

    missing_mandatory = customers[["customer_id", "customer_name", "kyc_status"]].isna().any(axis=1)
    issues.append(_issue("customers", "MISSING_MANDATORY_FIELD", "Missing mandatory customer field",
                          missing_mandatory, "customer_id", customers))

    return [i for i in issues if i.row_count > 0]


def validate_accounts(accounts: pd.DataFrame, customers: pd.DataFrame) -> list[DataQualityIssue]:
    issues = []
    now = pd.Timestamp.now()

    known_customers = set(customers["customer_id"])
    invalid_relationship = ~accounts["customer_id"].isin(known_customers)
    issues.append(_issue("accounts", "INVALID_CUSTOMER_RELATIONSHIP",
                          "Account references a customer_id not present in customers.csv",
                          invalid_relationship, "account_id", accounts))

    future_open = accounts["opening_date"] > now
    issues.append(_issue("accounts", "FUTURE_OPENING_DATE", "Future account opening date",
                          future_open, "account_id", accounts))

    dup_account = accounts["account_id"].duplicated(keep=False)
    issues.append(_issue("accounts", "DUPLICATE_ACCOUNT_ID", "Duplicate account_id",
                          dup_account, "account_id", accounts))

    invalid_status = ~accounts["account_status"].isin(["ACTIVE", "CLOSED", "DORMANT", "BLOCKED"])
    issues.append(_issue("accounts", "INVALID_ACCOUNT_STATUS", "Unrecognized account status value",
                          invalid_status, "account_id", accounts))

    negative_balance = accounts["current_balance"] < 0
    issues.append(_issue("accounts", "NEGATIVE_BALANCE", "Negative current balance",
                          negative_balance, "account_id", accounts))

    return [i for i in issues if i.row_count > 0]


def validate_transactions(transactions: pd.DataFrame, accounts: pd.DataFrame) -> list[DataQualityIssue]:
    issues = []
    now = pd.Timestamp.now()

    negative_amount = transactions["transaction_amount"] < 0
    issues.append(_issue("transactions", "NEGATIVE_AMOUNT", "Negative transaction amount",
                          negative_amount, "transaction_id", transactions))

    dup_txn = transactions["transaction_id"].duplicated(keep=False)
    issues.append(_issue("transactions", "DUPLICATE_TRANSACTION_ID", "Duplicate transaction_id",
                          dup_txn, "transaction_id", transactions))

    future_dated = transactions["transaction_datetime"] > now
    issues.append(_issue("transactions", "FUTURE_TRANSACTION_DATE", "Future-dated transaction",
                          future_dated, "transaction_id", transactions))

    invalid_currency = ~transactions["currency"].isin(ALLOWED_CURRENCIES)
    issues.append(_issue("transactions", "INVALID_CURRENCY", "Currency code not in allowed set",
                          invalid_currency, "transaction_id", transactions))

    known_accounts = set(accounts["account_id"])
    invalid_account = ~transactions["account_id"].isin(known_accounts)
    issues.append(_issue("transactions", "INVALID_ACCOUNT_REFERENCE",
                          "Transaction references an unknown account_id",
                          invalid_account, "transaction_id", transactions))

    settlement_inconsistent = (transactions["transaction_status"] == "SUCCESS") & (
        transactions["settlement_status"].isin(["FAILED"])
    )
    issues.append(_issue("transactions", "SETTLEMENT_INCONSISTENCY",
                          "Successful transaction with failed settlement",
                          settlement_inconsistent, "transaction_id", transactions))

    missing_ip = transactions["ip_address"].isna() | (transactions["ip_address"].astype(str).str.len() == 0)
    issues.append(_issue("transactions", "MISSING_IP_ADDRESS", "Missing IP address",
                          missing_ip, "transaction_id", transactions))

    missing_mandatory = transactions[["transaction_id", "account_id", "customer_id"]].isna().any(axis=1)
    issues.append(_issue("transactions", "MISSING_MANDATORY_FIELD", "Missing mandatory transaction field",
                          missing_mandatory, "transaction_id", transactions))

    return [i for i in issues if i.row_count > 0]


def validate_incidents(incidents: pd.DataFrame) -> list[DataQualityIssue]:
    issues = []

    missing_rca = incidents["root_cause"].isna() & (incidents["incident_status"] == "CLOSED")
    issues.append(_issue("incidents", "MISSING_ROOT_CAUSE", "Closed incident missing root cause",
                          missing_rca, "incident_id", incidents))

    missing_owner = incidents["assigned_engineer"].isna()
    issues.append(_issue("incidents", "MISSING_OWNERSHIP", "Incident missing assigned engineer",
                          missing_owner, "incident_id", incidents))

    resolution_delay = (
        incidents["resolved_datetime"].notna()
        & ((incidents["resolved_datetime"] - incidents["reported_datetime"]).dt.total_seconds() / 3600
           > incidents["sla_hours"])
    )
    issues.append(_issue("incidents", "RESOLUTION_DELAY", "Resolution time exceeded SLA hours",
                          resolution_delay, "incident_id", incidents))

    return [i for i in issues if i.row_count > 0]


def validate_api_logs(api_logs: pd.DataFrame) -> list[DataQualityIssue]:
    issues = []

    slow = api_logs["response_time_ms"] > api_logs.groupby("api_name")["response_time_ms"].transform(
        lambda s: s.quantile(0.95)
    )
    issues.append(_issue("api_logs", "SLOW_RESPONSE", "Response time above p95 for its API",
                          slow, "log_id", api_logs))

    http_failures = api_logs["response_code"] >= 500
    issues.append(_issue("api_logs", "HTTP_SERVER_ERROR", "HTTP 5xx failure",
                          http_failures, "log_id", api_logs))

    timeouts = api_logs["timeout_flag"] == "Y"
    issues.append(_issue("api_logs", "TIMEOUT", "Request timeout flagged",
                          timeouts, "log_id", api_logs))

    return [i for i in issues if i.row_count > 0]


def validate_test_cases(test_cases: pd.DataFrame) -> list[DataQualityIssue]:
    issues = []

    failed = test_cases["execution_status"] == "FAIL"
    issues.append(_issue("test_cases", "FAILED_TEST", "Test case failed",
                          failed, "test_case_id", test_cases))

    blocked = test_cases["execution_status"] == "BLOCKED"
    issues.append(_issue("test_cases", "BLOCKED_EXECUTION", "Test execution blocked (environment unavailable)",
                          blocked, "test_case_id", test_cases))

    return [i for i in issues if i.row_count > 0]


def validate_all(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    all_issues: list[DataQualityIssue] = []
    all_issues += validate_customers(frames["customers"])
    all_issues += validate_accounts(frames["accounts"], frames["customers"])
    all_issues += validate_transactions(frames["transactions"], frames["accounts"])
    all_issues += validate_incidents(frames["incidents"])
    all_issues += validate_api_logs(frames["api_logs"])
    all_issues += validate_test_cases(frames["test_cases"])

    if not all_issues:
        return pd.DataFrame(columns=["entity", "issue_code", "description", "row_count"])

    return pd.DataFrame(
        [
            {
                "entity": i.entity,
                "issue_code": i.issue_code,
                "description": i.description,
                "row_count": i.row_count,
            }
            for i in all_issues
        ]
    )
