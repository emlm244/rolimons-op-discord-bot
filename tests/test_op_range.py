import pytest

from rolimons_op_bot.op_range import calculate_op_range


def test_calculate_op_range_default_tolerance() -> None:
    assert calculate_op_range(65000, 12000) == (75200, 78800)


def test_calculate_op_range_custom_tolerance() -> None:
    assert calculate_op_range(100000, 20000, tolerance=0.1) == (118000, 122000)


@pytest.mark.parametrize(
    "base_value, average_op, tolerance",
    [(-1, 10, 0.1), (10, -5, 0.2), (10, 10, -0.1), (10, 10, 1.5)],
)
def test_calculate_op_range_rejects_invalid_inputs(
    base_value: int, average_op: int, tolerance: float
) -> None:
    with pytest.raises(ValueError):
        calculate_op_range(base_value, average_op, tolerance)
