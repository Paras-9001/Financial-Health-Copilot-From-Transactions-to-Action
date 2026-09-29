from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CsvConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_id: str = Field(min_length=20, max_length=100)
    column_mapping: dict[str, str] | None = None


class CsvPreviewResponse(BaseModel):
    preview_id: str
    headers: list[str]
    detected_mapping: dict[str, str]
    rows: list[dict[str, Any]]
    total_rows: int
    valid_rows: int
    invalid_rows: int


class CsvConfirmResponse(BaseModel):
    imported: int
    duplicates_skipped: int
    rejected: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    recalculation_triggered: bool
