"""Command helpers for composing Discord responses."""

from __future__ import annotations

from .data import ItemOPRange


def format_op_response(item: ItemOPRange) -> str:
    """Build a short, human-friendly OP range string for Discord.

    Parameters
    ----------
    item: ItemOPRange
        Structured OP range for a Rolimon's item.
    """

    formatted_range = f"{item.op_low:,}–{item.op_high:,} {item.currency}"
    return (
        f"Typical overpay for **{item.name}** (#{item.item_id}): "
        f"{formatted_range}. "
        "Values are estimates; check Rolimon's for live data."
    )
