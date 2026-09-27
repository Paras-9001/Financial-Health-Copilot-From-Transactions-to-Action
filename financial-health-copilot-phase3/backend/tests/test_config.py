import ast
import re
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core import config

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "CONFIGURATION.md"


def test_every_documented_named_default_matches_single_module():
    names = []
    for line in DOC.read_text().splitlines():
        match = re.match(r"\| `([A-Za-z_][A-Za-z_0-9]*)` \| ([^|]+)\|", line)
        if not match:
            continue
        name, raw = match.groups()
        name = name.upper()
        names.append(name)
        actual = getattr(config, name)  # Fails if any documented name is missing.
        if name == "CURRENCY":
            assert actual == raw.strip()
        else:
            expected = Decimal(re.search(r"[0-9]+(?:\.[0-9]+)?", raw).group())
            assert Decimal(str(actual)) == expected, name
    assert len(names) == 36


def test_all_consumer_assignments_use_config_instead_of_redefining_thresholds():
    policy_names = {name for name in vars(config) if name.isupper()}
    for path in (ROOT / "backend/app").rglob("*.py"):
        if path.name == "config.py" or "migrations" in path.parts:
            continue  # Historical migration defaults must remain frozen.
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    assert not (isinstance(target, ast.Name) and target.id in policy_names), str(path)


def test_confidence_bands_weights_and_unnamed_table_values():
    assert sum(getattr(config, n) for n in vars(config) if n.startswith("WEIGHT_")) == Decimal("1")
    assert config.CONFIDENCE_HIGH_MIN == Decimal("0.70")
    assert config.CONFIDENCE_MEDIUM_MIN == Decimal("0.40")
    assert config.CONFIDENCE_LOW_MIN == Decimal("0.25")
    assert config.SIMULATION_HORIZON_MAX_DAYS == 180
    assert [config.PREDICTION_ROUNDING_SMALL_CUTOFF, config.PREDICTION_ROUNDING_LARGE_CUTOFF] == [
        Decimal("1000"),
        Decimal("100000"),
    ]
    assert [
        config.PREDICTION_ROUNDING_SMALL_STEP,
        config.PREDICTION_ROUNDING_MEDIUM_STEP,
        config.PREDICTION_ROUNDING_LARGE_STEP,
    ] == [Decimal("10"), Decimal("100"), Decimal("1000")]


@pytest.mark.parametrize(
    "override", [{"jwt_secret": "short"}, {"cors_origins": ["*"]}, {"database_url": "sqlite://"}]
)
def test_invalid_runtime_configuration_fails_fast(override):
    with pytest.raises(ValidationError):
        config.Settings(**override)
