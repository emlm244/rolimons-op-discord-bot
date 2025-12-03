"""Tests for the scoring algorithm."""

import sys
sys.path.insert(0, ".")

import pytest
from src.data.models import Item, Demand, Trend
from src.sniper.scorer import SnipeScorer, ScoreTier
from src.config import StrategyFlag, UGCMode


@pytest.fixture
def scorer():
    """Create a scorer with default settings."""
    return SnipeScorer(
        strategies=[StrategyFlag.QUICK_FLIPS],
        ugc_mode=UGCMode.INCLUDE,
    )


@pytest.fixture
def good_item():
    """Create a good item for testing."""
    return Item(
        item_id=12345,
        name="Test Limited",
        rap=10000,
        value=10000,
        demand=Demand.HIGH,
        trend=Trend.STABLE,
        projected=False,
        hyped=False,
        rare=False,
        is_ugc=False,
        recent_sales_30d=30,
    )


@pytest.fixture
def projected_item():
    """Create a projected (bad) item."""
    return Item(
        item_id=99999,
        name="Projected Scam",
        rap=100000,
        value=50000,
        demand=Demand.LOW,
        trend=Trend.UNSTABLE,
        projected=True,  # PROJECTED - should be rejected
        hyped=True,
        rare=False,
        is_ugc=False,
    )


class TestScorer:
    """Test the SnipeScorer class."""

    def test_high_discount_high_demand_scores_well(self, scorer, good_item):
        """50% off + high demand should score EXCELLENT."""
        # 50% off
        listing_price = 5000
        result = scorer.score(good_item, listing_price)

        assert result.score >= 70  # Should be at least GOOD
        assert result.tier in (ScoreTier.EXCELLENT, ScoreTier.GOOD)
        assert result.discount_percent == 50.0

    def test_small_discount_scores_poorly(self, scorer, good_item):
        """10% off should be rejected."""
        # Only 10% off
        listing_price = 9000
        result = scorer.score(good_item, listing_price)

        assert result.score == 0
        assert result.tier == ScoreTier.REJECT

    def test_discount_calculation(self, scorer, good_item):
        """Verify discount percentage is calculated correctly."""
        listing_price = 7000  # 30% off from value of 10000
        result = scorer.score(good_item, listing_price)

        assert abs(result.discount_percent - 30.0) < 0.01  # Allow small float diff

    def test_demand_affects_score(self, scorer):
        """Higher demand should result in higher base score (before cap)."""
        base_item = Item(
            item_id=1,
            name="Test",
            rap=10000,
            value=10000,
            trend=Trend.STABLE,
            projected=False,
            recent_sales_30d=20,
        )

        # Test with different demand levels at same price (30% off - lower to avoid cap)
        price = 7000

        low_demand = Item(**{**base_item.__dict__, "demand": Demand.LOW})
        high_demand = Item(**{**base_item.__dict__, "demand": Demand.HIGH})
        amazing_demand = Item(**{**base_item.__dict__, "demand": Demand.AMAZING})

        low_result = scorer.score(low_demand, price)
        high_result = scorer.score(high_demand, price)
        amazing_result = scorer.score(amazing_demand, price)

        # Check base scores (before capping at 100)
        assert amazing_result.breakdown.demand_score > high_result.breakdown.demand_score > low_result.breakdown.demand_score

    def test_trend_affects_score(self, scorer):
        """Rising trend should score better than falling."""
        base_item = Item(
            item_id=1,
            name="Test",
            rap=10000,
            value=10000,
            demand=Demand.NORMAL,
            projected=False,
            recent_sales_30d=20,
        )

        price = 5000  # 50% off

        lowering = Item(**{**base_item.__dict__, "trend": Trend.LOWERING})
        stable = Item(**{**base_item.__dict__, "trend": Trend.STABLE})
        raising = Item(**{**base_item.__dict__, "trend": Trend.RAISING})

        lowering_result = scorer.score(lowering, price)
        stable_result = scorer.score(stable, price)
        raising_result = scorer.score(raising, price)

        assert raising_result.score > stable_result.score > lowering_result.score

    def test_rare_bonus(self, scorer, good_item):
        """Rare items with high demand should get bonus."""
        normal_item = good_item
        rare_item = Item(**{**good_item.__dict__, "rare": True})

        price = 5000  # 50% off

        normal_result = scorer.score(normal_item, price)
        rare_result = scorer.score(rare_item, price)

        # Rare + High demand = +5 bonus
        # Note: final scores may both cap at 100, so check breakdown
        assert rare_result.breakdown.rare_bonus == 5
        assert normal_result.breakdown.rare_bonus == 0
        # Base score should be higher for rare item
        assert rare_result.breakdown.base_score > normal_result.breakdown.base_score

    def test_ugc_penalty(self, scorer):
        """UGC items should receive penalty."""
        classic_item = Item(
            item_id=1,
            name="Classic",
            rap=10000,
            value=10000,
            demand=Demand.HIGH,
            trend=Trend.STABLE,
            is_ugc=False,
            recent_sales_30d=20,
        )
        ugc_item = Item(**{**classic_item.__dict__, "is_ugc": True})

        price = 5000

        classic_result = scorer.score(classic_item, price)
        ugc_result = scorer.score(ugc_item, price)

        assert classic_result.score > ugc_result.score
        assert ugc_result.breakdown.ugc_penalty < 0

    def test_batch_scoring(self, scorer, good_item):
        """Test scoring multiple items at once."""
        items_with_prices = [
            (good_item, 5000),  # 50% off
            (good_item, 7000),  # 30% off
            (good_item, 8000),  # 20% off
        ]

        results = scorer.score_batch(items_with_prices)

        # Should be sorted by score (highest first)
        assert results[0].score >= results[1].score >= results[2].score

    def test_score_tier_classification(self):
        """Verify tier boundaries."""
        assert ScoreTier.from_score(100) == ScoreTier.EXCELLENT
        assert ScoreTier.from_score(85) == ScoreTier.EXCELLENT
        assert ScoreTier.from_score(84) == ScoreTier.GOOD
        assert ScoreTier.from_score(70) == ScoreTier.GOOD
        assert ScoreTier.from_score(69) == ScoreTier.RISKY
        assert ScoreTier.from_score(50) == ScoreTier.RISKY
        assert ScoreTier.from_score(49) == ScoreTier.REJECT
        assert ScoreTier.from_score(0) == ScoreTier.REJECT


class TestFilters:
    """Test pre-filters."""

    def test_projected_item_rejected(self, projected_item):
        """Projected items should be rejected."""
        from src.analysis.filters import PreFilter

        pre_filter = PreFilter()
        result = pre_filter.filter(projected_item, 1000)

        assert not result.passed
        assert "projected" in result.reason.value.lower()

    def test_terrible_demand_rejected(self):
        """Items with terrible demand should be rejected."""
        from src.analysis.filters import PreFilter

        item = Item(
            item_id=1,
            name="Bad Item",
            rap=1000,
            value=1000,
            demand=Demand.TERRIBLE,
            trend=Trend.STABLE,
        )

        pre_filter = PreFilter()
        result = pre_filter.filter(item, 500)

        assert not result.passed

    def test_good_item_passes(self, good_item):
        """Good items at good price should pass."""
        from src.analysis.filters import PreFilter

        pre_filter = PreFilter()
        result = pre_filter.filter(good_item, 5000)  # 50% off

        assert result.passed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
