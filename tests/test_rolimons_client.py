from __future__ import annotations

import pytest

from rolimons_bot.rolimons_client import (
    ItemDetails,
    ParsingError,
    parse_item_page,
    percentile_bands,
)

SAMPLE_HTML = """
<script>
item_details_data = {"item_id":123,"item_name":"Test Item","rap":1000,"value":1200,
"acronym":"TI","demand":2,"trend":1,"projected":false,"hyped":true,"rare":false,
"thumbnail_url_lg":"https://example.com/img.png"};
history_data = {"num_points":3,"timestamp":[1700000000,1700100000,1700200000],
"rap":[900,1000,1050],"best_price":[1000,1200,1300],"num_sellers":[1,2,3]};
</script>
"""


def test_parse_item_page_extracts_fields() -> None:
    details, history = parse_item_page(SAMPLE_HTML, 123)
    assert isinstance(details, ItemDetails)
    assert details.name == "Test Item"
    assert details.value == 1200
    assert details.acronym == "TI"
    assert history.rap_history == [900, 1000, 1050]
    assert history.best_price_history[-1] == 1300


def test_last_month_ops_filters_recent() -> None:
    _, history = parse_item_page(SAMPLE_HTML, 123)
    now = 1700200000 + (5 * 24 * 60 * 60)
    ops = history.last_month_ops(now=now)
    assert ops == [100, 200, 250]


def test_percentile_bands() -> None:
    bands = percentile_bands([0, 50, 100, 150])
    assert bands == (38, 75, 112)


def test_parse_with_wrong_id() -> None:
    with pytest.raises(ParsingError):
        parse_item_page(SAMPLE_HTML, 1)
