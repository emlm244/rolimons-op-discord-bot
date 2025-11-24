import pytest

from rolimons_op_bot.commands import CommandArgs, parse_op_command


def test_parse_op_command_basic() -> None:
    args = parse_op_command("item:Valk value:65000 op:12000")
    assert args == CommandArgs(item_name="Valk", base_value=65000, average_op=12000)


def test_parse_op_command_allows_extra_fields() -> None:
    args = parse_op_command("item:Valk value:65000 op:12000 user:abc")
    assert args.item_name == "Valk"
    assert args.base_value == 65000
    assert args.average_op == 12000


def test_parse_op_command_missing_fields() -> None:
    with pytest.raises(ValueError):
        parse_op_command("item:Valk value:65000")


@pytest.mark.parametrize("input_text", ["", "   ", "item:	 op:20 value:10"])
def test_parse_op_command_rejects_blank_or_partial(input_text: str) -> None:
    with pytest.raises(ValueError):
        parse_op_command(input_text)
