from collections import Counter

import pytest
from pydantic import ValidationError

from housing.data.generate import CONFIG_PATH, GeneratorConfig, encode_csv, generate
from housing.data.store import parse_csv


def test_generator_byte_determinism_and_recipe_support() -> None:
    config = GeneratorConfig.model_validate_json(CONFIG_PATH.read_bytes())
    first = generate(config)
    second = generate(config)
    data = encode_csv(first)
    assert encode_csv(second) == data
    assert b"\r" not in data and data.endswith(b"\n") and not data.startswith(b"\xef\xbb\xbf")
    assert len(first) == 34560 and len({r.record_id for r in first}) == 34560
    assert len({r.listing_id for r in first}) == 1440
    assert set(Counter(r.month for r in first).values()) == {1440}
    assert set(Counter((r.month, r.zip) for r in first).values()) == {120}
    assert all(
        500 <= r.sqft <= 5000 and 8_000_000 <= r.price_cents <= 200_000_000 and r.price_cents % 100 == 0
        for r in first
    )
    parsed = parse_csv(data)
    assert parsed.rows == first and not parsed.quarantine
    assert first[0].record_id == "obs-00-00-000" and first[-1].record_id == "obs-23-11-119"


def test_generator_rejects_unlocked_runtime_and_inconsistent_dimensions() -> None:
    config = GeneratorConfig.model_validate_json(CONFIG_PATH.read_bytes())
    with pytest.raises(RuntimeError, match="requires Python"):
        generate(config.model_copy(update={"python_version": "3.12.0"}))
    payload = config.model_dump(mode="json")
    payload["expected_rows"] = 1
    with pytest.raises(ValidationError):
        GeneratorConfig.model_validate(payload)
