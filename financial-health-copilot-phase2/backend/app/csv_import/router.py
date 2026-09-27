import json

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core import config
from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import current_user
from app.csv_import.schemas import CsvConfirmRequest, CsvConfirmResponse, CsvPreviewResponse
from app.csv_import.service import (
    confirm_import,
    detect_mapping,
    parse_csv,
    preview_rows,
    validate_mapping,
)
from app.csv_import.store import preview_store
from app.db.user import User

router = APIRouter(prefix="/imports/csv", tags=["CSV Import"])


@router.post("/preview", response_model=CsvPreviewResponse)
async def preview_csv(
    file: UploadFile = File(...),
    column_mapping: str | None = Form(default=None),
    user: User = Depends(current_user),
):
    allowed_types = {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
        None,
    }
    if file.content_type not in allowed_types and not (file.filename or "").lower().endswith(".csv"):
        raise APIError(415, "unsupported_file_type", "Upload a CSV file.")
    content = await file.read(config.CSV_UPLOAD_MAX_BYTES + 1)
    headers, rows = parse_csv(content)
    if column_mapping:
        try:
            mapping = json.loads(column_mapping)
        except json.JSONDecodeError as exc:
            raise APIError(422, "invalid_column_mapping", "Column mapping must be JSON.") from exc
        if not isinstance(mapping, dict):
            raise APIError(422, "invalid_column_mapping", "Column mapping must be an object.")
    else:
        mapping = detect_mapping(headers)
    validate_mapping(mapping, headers)
    validated = preview_rows(rows, mapping)
    preview_id = preview_store.put(user.id, headers, rows, mapping)
    invalid = sum(bool(row["errors"]) for row in validated)
    return {
        "preview_id": preview_id,
        "headers": headers,
        "detected_mapping": mapping,
        "rows": validated[: config.CSV_PREVIEW_ROWS],
        "total_rows": len(rows),
        "valid_rows": len(rows) - invalid,
        "invalid_rows": invalid,
    }


@router.post("/confirm", response_model=CsvConfirmResponse)
def confirm_csv(
    data: CsvConfirmRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    preview = preview_store.get(data.preview_id, user.id)
    if preview is None:
        raise APIError(404, "preview_expired", "Upload and preview the CSV again.")
    mapping = data.column_mapping or preview.mapping
    validate_mapping(mapping, preview.headers)
    result = confirm_import(db, user.id, preview.rows, mapping)
    preview_store.consume(data.preview_id)
    return result
