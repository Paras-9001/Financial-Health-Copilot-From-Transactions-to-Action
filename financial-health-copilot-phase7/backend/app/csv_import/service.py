import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.accounts.repository import AccountRepository
from app.core import config
from app.core.errors import APIError
from app.transactions.service import ingest_transactions

REQUIRED_FIELDS = ("date", "amount", "direction", "description", "account_name")
ALIASES = {
    "date": {"date", "transaction_date", "txn_date", "posted_date"},
    "amount": {"amount", "value", "transaction_amount"},
    "direction": {"direction", "type", "debit_credit", "dr_cr"},
    "description": {"description", "merchant", "narration", "details"},
    "account_name": {"account_name", "account", "account_label"},
}


def parse_csv(content: bytes) -> tuple[list[str], list[dict[str, str]]]:
    if len(content) > config.CSV_UPLOAD_MAX_BYTES:
        raise APIError(413, "file_too_large", "CSV must be 2 MB or smaller.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise APIError(422, "invalid_csv", "CSV must use UTF-8 encoding.") from exc
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise APIError(422, "invalid_csv", "CSV must contain a header row.")
    headers = [header.strip() for header in reader.fieldnames if header]
    rows = []
    for raw in reader:
        if len(rows) >= config.CSV_UPLOAD_MAX_ROWS:
            raise APIError(413, "too_many_rows", "CSV must contain at most 5,000 rows.")
        rows.append({str(key).strip(): str(value or "").strip() for key, value in raw.items() if key})
    if not rows:
        raise APIError(422, "invalid_csv", "CSV must contain at least one data row.")
    return headers, rows


def detect_mapping(headers: list[str]) -> dict[str, str]:
    normalized = {header.strip().lower(): header for header in headers}
    mapping = {}
    for field, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[field] = normalized[alias]
                break
    return mapping


def validate_mapping(mapping: dict[str, str], headers: list[str]) -> None:
    missing = [field for field in REQUIRED_FIELDS if field not in mapping]
    unknown = [column for column in mapping.values() if column not in headers]
    if missing or unknown:
        raise APIError(
            422,
            "invalid_column_mapping",
            "Map every required field to an existing CSV column.",
            {"missing_fields": missing, "unknown_columns": unknown},
        )


def validate_row(raw: dict[str, str], mapping: dict[str, str], row_number: int) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    extracted = {field: raw.get(mapping[field], "").strip() for field in REQUIRED_FIELDS}
    try:
        parsed_date = date.fromisoformat(extracted["date"])
    except ValueError:
        parsed_date = None
        errors.append({"field": "date", "message": "Use an ISO date such as 2026-09-27"})
    try:
        parsed_amount = Decimal(extracted["amount"].replace(",", ""))
        if parsed_amount == 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        parsed_amount = None
        errors.append({"field": "amount", "message": "Enter a non-zero numeric amount"})
    direction = extracted["direction"].lower()
    if direction not in {"debit", "credit"}:
        errors.append({"field": "direction", "message": "Use debit or credit"})
    if not extracted["description"]:
        errors.append({"field": "description", "message": "Description is required"})
    if not extracted["account_name"]:
        errors.append({"field": "account_name", "message": "Account name is required"})
    return {
        "row": row_number,
        "source": raw,
        "errors": errors,
        "parsed": {
            "txn_date": parsed_date,
            "amount": abs(parsed_amount) if parsed_amount is not None else None,
            "direction": direction,
            "raw_description": extracted["description"],
            "account_name": extracted["account_name"],
        },
    }


def preview_rows(rows: list[dict[str, str]], mapping: dict[str, str]) -> list[dict[str, Any]]:
    return [validate_row(raw, mapping, index) for index, raw in enumerate(rows, start=2)]


def confirm_import(
    db: Session, user_id: UUID, rows: list[dict[str, str]], mapping: dict[str, str]
) -> dict[str, Any]:
    validated = preview_rows(rows, mapping)
    rejected = [{"row": row["row"], "errors": row["errors"]} for row in validated if row["errors"]]
    accounts = AccountRepository(db)
    transaction_rows = []
    source_rows = []
    for row in validated:
        if row["errors"]:
            continue
        parsed = row["parsed"]
        account = accounts.get_or_create_checking(user_id, parsed.pop("account_name"))
        transaction_rows.append({**parsed, "account_id": account.id})
        source_rows.append(row["row"])
    result = (
        ingest_transactions(db, user_id, transaction_rows, update_balances=True)
        if transaction_rows
        else {
            "ingested": 0,
            "duplicates_skipped": 0,
            "warnings": [],
            "recalculation_triggered": False,
            "rejected": [],
        }
    )
    for item in result["rejected"]:
        source_index = item["row"] - 1
        item["row"] = source_rows[source_index]
        rejected.append(item)
    for warning in result["warnings"]:
        source_index = warning["row"] - 1
        warning["row"] = source_rows[source_index]
    return {
        "imported": result["ingested"],
        "duplicates_skipped": result["duplicates_skipped"],
        "rejected": sorted(rejected, key=lambda item: item["row"]),
        "warnings": result["warnings"],
        "recalculation_triggered": result["recalculation_triggered"],
    }
