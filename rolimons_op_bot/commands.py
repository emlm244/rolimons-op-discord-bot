import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandArgs:
    """Parsed command arguments for OP range queries."""

    item_name: str
    base_value: int
    average_op: int


_TOKEN_PATTERN = re.compile(r"(?P<key>\w+):(?P<value>[^\s]+)")


def parse_op_command(command_text: str) -> CommandArgs:
    """Parse a slash command text payload into structured arguments.

    The parser accepts whitespace-separated ``key:value`` pairs, requiring
    ``item`` (string), ``value`` (int), and ``op`` (int). Unknown keys are
    ignored to keep the parser forward compatible with Discord slash
    commands that may include extra metadata.

    Raises:
        ValueError: if required fields are missing or cannot be converted.
    """

    if not command_text.strip():
        raise ValueError("Command text cannot be empty.")

    fields: dict[str, str] = {}
    for match in _TOKEN_PATTERN.finditer(command_text):
        key = match.group("key").lower()
        value = match.group("value")
        fields[key] = value

    missing = [key for key in ("item", "value", "op") if key not in fields]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(sorted(missing))}")

    try:
        base_value = int(fields["value"].replace(",", ""))
        average_op = int(fields["op"].replace(",", ""))
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError("Value and op must be integers") from exc

    item_name = fields["item"].replace("_", " ").strip()
    if not item_name:
        raise ValueError("Item name cannot be blank")

    return CommandArgs(item_name=item_name, base_value=base_value, average_op=average_op)
