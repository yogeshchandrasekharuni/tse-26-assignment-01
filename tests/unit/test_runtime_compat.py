import pytest

from housing.runtime_compat import frozen_parameter_order


def test_only_provider_metadata_order_can_change() -> None:
    frozen = "seed       104729\ntemperature   0.2\nnum_ctx     65536"
    actual = "num_ctx     65536\nseed       104729\ntemperature   0.2"
    assert frozen_parameter_order(actual, frozen) == frozen


@pytest.mark.parametrize(
    "actual",
    [
        "seed 104729\ntemperature 0.25\nnum_ctx 65536",
        "seed 130363\ntemperature 0.2\nnum_ctx 65536",
        "seed 104729\ntemperature 0.2",
        "seed 104729\ntemperature 0.2\nnum_ctx 65536\nseed 104729",
    ],
)
def test_changed_values_missing_and_duplicate_parameters_fail_closed(actual: str) -> None:
    with pytest.raises(ValueError):
        frozen_parameter_order(actual, "seed 104729\ntemperature 0.2\nnum_ctx 65536")
