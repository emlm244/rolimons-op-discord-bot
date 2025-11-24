from __future__ import annotations

DEFAULT_TOLERANCE = 0.15


def calculate_op_range(
    base_value: int, average_op: int, tolerance: float = DEFAULT_TOLERANCE
) -> tuple[int, int]:
    """Calculate a recommended OP range given Rolimon's average.

    Args:
        base_value: Current Rolimon's value for the limited item.
        average_op: Average overpay reported for recent trades.
        tolerance: Percentage range (0-1) to apply above/below the average.

    Returns:
        A tuple of ``(min_offer, max_offer)`` integers rounded to the nearest
        whole Robux.

    Raises:
        ValueError: if any input is negative or tolerance outside 0-1.
    """

    if base_value < 0 or average_op < 0:
        raise ValueError("Values cannot be negative")
    if not 0 <= tolerance <= 1:
        raise ValueError("Tolerance must be between 0 and 1")

    delta = average_op * tolerance
    min_offer = int(round(base_value + average_op - delta))
    max_offer = int(round(base_value + average_op + delta))
    return min_offer, max_offer
