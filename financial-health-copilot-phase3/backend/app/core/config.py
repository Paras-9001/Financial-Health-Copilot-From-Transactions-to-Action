"""Single source of runtime settings and financial defaults from CONFIGURATION.md.

Percent-suffixed values are percentage points: 30 means 30%, not 0.30.
CVs, confidence weights and scores are dimensionless Decimal fractions.
Financial algorithms belong to later phases; this module only defines policy.
"""

from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PREFERRED_BUFFER_DAYS = 7
CURRENCY = "INR"
FORECAST_HORIZON_DEFAULT_DAYS = 30
LOW_BUFFER_DAYS_HIGH = 2
LOW_BUFFER_DAYS_MEDIUM = 5
SPENDING_SPIKE_PCT = Decimal("30")
RECURRING_BURDEN_PCT = Decimal("50")
DEBT_SERVICE_RATIO_HIGH = Decimal("40")
CREDIT_UTILIZATION_HIGH = Decimal("70")
INCOME_CV_HIGH = Decimal("0.30")
UNUSUAL_TXN_MULTIPLIER = Decimal("3.0")
MIN_PERIODS_FOR_VOLATILITY = 3
RECURRING_AMOUNT_TOLERANCE_PCT = Decimal("10")
RECURRING_INTERVAL_TOLERANCE_DAYS_MONTHLY = 3
RECURRING_INTERVAL_TOLERANCE_DAYS_WEEKLY = 3
RECURRING_INTERVAL_TOLERANCE_DAYS_YEARLY = 7
RECURRING_MIN_CONFIRMED_CYCLES = 2
FORECAST_HORIZON_MAX_DAYS = 90
SIMULATION_HORIZON_MAX_DAYS = 180
FORECAST_TREND_CAP_PCT = Decimal("15")
FORECAST_CONFIDENCE_HIGH_MIN_MONTHS_HISTORY = 3
FORECAST_CONFIDENCE_HIGH_MAX_SPENDING_CV = Decimal("0.15")
FORECAST_CONFIDENCE_MEDIUM_MAX_SPENDING_CV = Decimal("0.35")
FORECAST_CONFIDENCE_HIGH_MIN_RECURRING_COVERAGE_PCT = Decimal("80")
WEIGHT_DATA_COMPLETENESS = Decimal("0.30")
WEIGHT_DATA_FRESHNESS = Decimal("0.20")
WEIGHT_HISTORICAL_CONSISTENCY = Decimal("0.20")
WEIGHT_FORECAST_UNCERTAINTY = Decimal("0.20")
WEIGHT_OBSERVATION_COUNT = Decimal("0.10")
OBSERVATION_COUNT_CAP_PERIODS = 6
CONFIDENCE_HIGH_MIN = Decimal("0.70")
CONFIDENCE_MEDIUM_MIN = Decimal("0.40")
CONFIDENCE_LOW_MIN = Decimal("0.25")
MIN_RECOMMENDATION_CONFIDENCE = Decimal("0.40")
MIN_HISTORY_CYCLES_FOR_RECOMMENDATION = 2
PRIORITY_SCORE_P0_MIN = Decimal("2.0")
PRIORITY_SCORE_P1_MIN = Decimal("1.0")
SEVERITY_WEIGHT_HIGH = 3
SEVERITY_WEIGHT_MEDIUM = 2
SEVERITY_WEIGHT_LOW = 1
PREDICTION_ROUNDING_SMALL_CUTOFF = Decimal("1000")
PREDICTION_ROUNDING_LARGE_CUTOFF = Decimal("100000")
PREDICTION_ROUNDING_SMALL_STEP = Decimal("10")
PREDICTION_ROUNDING_MEDIUM_STEP = Decimal("100")
PREDICTION_ROUNDING_LARGE_STEP = Decimal("1000")
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_BYTES = 72  # bcrypt's byte limit; reject instead of truncate
BCRYPT_ROUNDS = 12
CSV_UPLOAD_MAX_BYTES = 2_000_000
CSV_UPLOAD_MAX_ROWS = 5_000
CSV_PREVIEW_ROWS = 10
CSV_PREVIEW_TTL_SECONDS = 1_800
SUPPORTED_HISTORY_MONTHS = 24
API_PREFIX = "/api/v1"
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "financial-health-copilot"
JWT_AUDIENCE = "financial-health-copilot-api"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")
    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr
    jwt_secret: SecretStr
    access_token_minutes: int = Field(default=30, ge=1, le=1440)
    cors_origins: list[str] = ["http://localhost:3000"]
    auth_rate_limit: int = Field(default=10, ge=1, le=1000)
    auth_rate_window_seconds: int = Field(default=60, ge=1)
    auth_rate_max_clients: int = Field(default=10000, ge=1)
    llm_api_key: SecretStr | None = None  # Not used until Phase 5.
    llm_model: str | None = None

    @field_validator("jwt_secret")
    @classmethod
    def validate_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if len(secret) < 32 or "replace" in secret.lower() or "change" in secret.lower():
            raise ValueError("JWT_SECRET must be a generated secret of at least 32 characters")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use postgresql+psycopg://")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, value: list[str]) -> list[str]:
        if not value or any(v == "*" or not v.startswith(("http://", "https://")) for v in value):
            raise ValueError("Set explicit HTTP(S) frontend origins; wildcard is not allowed")
        return [v.rstrip("/") for v in value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
