"""Discord embed builders for RISniper."""

from __future__ import annotations

import discord
from datetime import datetime
from typing import Optional

from src.sniper.scorer import ScoreResult, ScoreTier
from src.sniper.engine import Opportunity, EngineState
from src.data.models import Item, PortfolioStats


# Color scheme
COLORS = {
    ScoreTier.EXCELLENT: discord.Color.green(),
    ScoreTier.GOOD: discord.Color.gold(),
    ScoreTier.RISKY: discord.Color.orange(),
    ScoreTier.REJECT: discord.Color.red(),
    "success": discord.Color.green(),
    "error": discord.Color.red(),
    "info": discord.Color.blue(),
    "warning": discord.Color.orange(),
}


def build_opportunity_embed(opportunity: Opportunity) -> discord.Embed:
    """Build an embed for a snipe opportunity alert."""
    result = opportunity.score_result
    item = result.item
    listing = opportunity.listing

    embed = discord.Embed(
        title=f"SNIPE OPPORTUNITY DETECTED",
        description=f"**{item.name}**",
        color=COLORS.get(result.tier, discord.Color.blue()),
        timestamp=opportunity.detected_at,
    )

    # Score field
    embed.add_field(
        name="Score",
        value=f"**{result.score}/100** {result.tier.emoji} {result.tier.display_name}",
        inline=True,
    )

    # Price info
    embed.add_field(
        name="Price",
        value=f"**{listing.price:,} R$** ({result.discount_percent:.1f}% off)",
        inline=True,
    )

    # Value info
    embed.add_field(
        name="Value / RAP",
        value=f"{item.value:,} R$ / {item.rap:,} R$",
        inline=True,
    )

    # Demand & Trend
    embed.add_field(
        name="Demand",
        value=item.display_demand,
        inline=True,
    )

    embed.add_field(
        name="Trend",
        value=item.display_trend,
        inline=True,
    )

    # Item type
    embed.add_field(
        name="Type",
        value=item.item_type,
        inline=True,
    )

    # Flags
    flags = []
    if item.rare:
        flags.append("Rare")
    if item.hyped:
        flags.append("Hyped")
    if item.projected:
        flags.append("PROJECTED")

    if flags:
        embed.add_field(
            name="Flags",
            value=", ".join(flags),
            inline=True,
        )

    # Score breakdown
    breakdown = result.breakdown
    breakdown_text = (
        f"Discount: +{breakdown.discount_score}\n"
        f"Demand: +{breakdown.demand_score}\n"
        f"Trend: +{breakdown.trend_score}\n"
        f"Liquidity: +{breakdown.liquidity_score}\n"
        f"Stability: +{breakdown.stability_score}"
    )
    if breakdown.strategy_modifier != 0:
        breakdown_text += f"\nStrategy: {'+' if breakdown.strategy_modifier > 0 else ''}{breakdown.strategy_modifier}"

    embed.add_field(
        name="Score Breakdown",
        value=f"```{breakdown_text}```",
        inline=False,
    )

    # Thumbnail
    embed.set_thumbnail(url=item.thumbnail_url)

    # Footer
    embed.set_footer(text=f"Item ID: {item.item_id} | Seller: {listing.seller_name}")

    return embed


def build_analyze_embed(result: ScoreResult) -> discord.Embed:
    """Build an embed for /analyze command results."""
    item = result.item

    embed = discord.Embed(
        title=f"Analysis: {item.name}",
        color=COLORS.get(result.tier, discord.Color.blue()),
        timestamp=datetime.utcnow(),
    )

    # Score
    embed.add_field(
        name="Snipe Score",
        value=f"**{result.score}/100** {result.tier.emoji}",
        inline=True,
    )

    # Price analyzed at
    embed.add_field(
        name="At Price",
        value=f"{result.listing_price:,} R$",
        inline=True,
    )

    # Discount
    embed.add_field(
        name="Discount",
        value=f"{result.discount_percent:.1f}%",
        inline=True,
    )

    # Item stats
    embed.add_field(
        name="Value",
        value=f"{item.value:,} R$",
        inline=True,
    )

    embed.add_field(
        name="RAP",
        value=f"{item.rap:,} R$",
        inline=True,
    )

    embed.add_field(
        name="Type",
        value=item.item_type,
        inline=True,
    )

    # Metrics
    embed.add_field(
        name="Demand",
        value=item.display_demand,
        inline=True,
    )

    embed.add_field(
        name="Trend",
        value=item.display_trend,
        inline=True,
    )

    # Flags
    flags = []
    if item.rare:
        flags.append("Rare")
    if item.hyped:
        flags.append("Hyped")
    if item.projected:
        flags.append("PROJECTED")
    embed.add_field(
        name="Flags",
        value=", ".join(flags) if flags else "None",
        inline=True,
    )

    # Full breakdown
    b = result.breakdown
    breakdown_lines = [
        f"Discount:   +{b.discount_score:2d}",
        f"Demand:     +{b.demand_score:2d}",
        f"Trend:      +{b.trend_score:2d}",
        f"Liquidity:  +{b.liquidity_score:2d}",
        f"Stability:  +{b.stability_score:2d}",
        f"Rare Bonus: +{b.rare_bonus:2d}",
        f"Classic:    +{b.classic_bonus:2d}",
        f"Hype Pen:   {b.hype_penalty:+3d}",
        f"UGC Pen:    {b.ugc_penalty:+3d}",
        f"Strategy:   {b.strategy_modifier:+3d}",
        f"{'─' * 16}",
        f"TOTAL:      {b.final_score:3d}",
    ]

    embed.add_field(
        name="Score Breakdown",
        value=f"```\n" + "\n".join(breakdown_lines) + "\n```",
        inline=False,
    )

    # Recommendation
    if result.tier == ScoreTier.EXCELLENT:
        rec = "Strong buy! High-confidence opportunity."
    elif result.tier == ScoreTier.GOOD:
        rec = "Good opportunity. Consider buying."
    elif result.tier == ScoreTier.RISKY:
        rec = "Risky. Proceed with caution."
    else:
        rec = "Not recommended. Score too low."

    embed.add_field(
        name="Recommendation",
        value=rec,
        inline=False,
    )

    embed.set_thumbnail(url=item.thumbnail_url)
    embed.set_footer(text=f"Item ID: {item.item_id}")

    return embed


def build_status_embed(status: dict) -> discord.Embed:
    """Build an embed for /snipe status command."""
    state = status.get("state", "unknown")
    stats = status.get("stats", {})
    cfg = status.get("config", {})

    # State color
    state_colors = {
        "running": discord.Color.green(),
        "stopped": discord.Color.red(),
        "paused": discord.Color.orange(),
        "starting": discord.Color.blue(),
        "stopping": discord.Color.orange(),
    }

    embed = discord.Embed(
        title="Sniper Status",
        color=state_colors.get(state, discord.Color.grey()),
        timestamp=datetime.utcnow(),
    )

    # State
    state_emoji = {
        "running": "",
        "stopped": "",
        "paused": "",
    }
    embed.add_field(
        name="State",
        value=f"{state_emoji.get(state, '')} **{state.upper()}**",
        inline=True,
    )

    # Uptime
    if stats.get("started_at"):
        embed.add_field(
            name="Started",
            value=stats["started_at"][:19].replace("T", " "),
            inline=True,
        )

    # Last scan
    if stats.get("last_scan_at"):
        embed.add_field(
            name="Last Scan",
            value=stats["last_scan_at"][:19].replace("T", " "),
            inline=True,
        )

    # Stats
    embed.add_field(
        name="Items Scanned",
        value=f"{stats.get('items_scanned', 0):,}",
        inline=True,
    )

    embed.add_field(
        name="Opportunities",
        value=f"{stats.get('opportunities_found', 0):,}",
        inline=True,
    )

    embed.add_field(
        name="Purchases",
        value=f"{stats.get('purchases_successful', 0)}/{stats.get('purchases_attempted', 0)}",
        inline=True,
    )

    embed.add_field(
        name="Total Spent",
        value=f"{stats.get('total_spent', 0):,} R$",
        inline=True,
    )

    embed.add_field(
        name="Errors",
        value=str(stats.get("errors", 0)),
        inline=True,
    )

    # Config
    config_text = (
        f"Mode: {cfg.get('purchase_mode', 'N/A')}\n"
        f"Threshold: {cfg.get('snipe_threshold', 70)}\n"
        f"Max Price: {cfg.get('max_price_per_item', 0):,} R$\n"
        f"Poll: {cfg.get('poll_interval', 60)}s"
    )
    embed.add_field(
        name="Configuration",
        value=f"```{config_text}```",
        inline=False,
    )

    return embed


def build_stats_embed(stats: PortfolioStats, records: list = None) -> discord.Embed:
    """Build an embed for /stats command."""
    embed = discord.Embed(
        title="SNIPER STATISTICS",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )

    # Portfolio value
    pnl_emoji = "" if stats.unrealized_pnl >= 0 else ""
    portfolio_text = (
        f"Total Spent: {stats.total_spent:,} R$\n"
        f"Current Value: {stats.current_value:,} R$\n"
        f"Unrealized P&L: {pnl_emoji} {stats.unrealized_pnl:+,} R$ ({stats.unrealized_pnl_percent:+.1f}%)\n"
        f"Realized P&L: {stats.realized_pnl:+,} R$"
    )
    embed.add_field(
        name="Portfolio Value",
        value=f"```{portfolio_text}```",
        inline=False,
    )

    # Performance
    perf_text = (
        f"Total Snipes: {stats.total_purchases}\n"
        f"Successful: {stats.successful_purchases}\n"
        f"Win Rate: {stats.win_rate:.1f}%\n"
        f"Success Rate: {stats.success_rate:.1f}%"
    )
    embed.add_field(
        name="Performance",
        value=f"```{perf_text}```",
        inline=True,
    )

    # W/L
    wl_text = (
        f"Winners: {stats.winning_trades}\n"
        f"Losers: {stats.losing_trades}"
    )
    embed.add_field(
        name="Win/Loss",
        value=f"```{wl_text}```",
        inline=True,
    )

    return embed


def build_config_embed(current_config: dict) -> discord.Embed:
    """Build an embed showing current configuration."""
    embed = discord.Embed(
        title="Sniper Configuration",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow(),
    )

    embed.add_field(
        name="Purchase Mode",
        value=f"`{current_config.get('purchase_mode', 'alert_confirm')}`",
        inline=True,
    )

    embed.add_field(
        name="Strategies",
        value=", ".join(f"`{s}`" for s in current_config.get('strategies', ['quick_flips'])),
        inline=True,
    )

    embed.add_field(
        name="UGC Mode",
        value=f"`{current_config.get('ugc_mode', 'include')}`",
        inline=True,
    )

    embed.add_field(
        name="Snipe Threshold",
        value=f"`{current_config.get('snipe_threshold', 70)}`",
        inline=True,
    )

    embed.add_field(
        name="Alert Threshold",
        value=f"`{current_config.get('alert_threshold', 50)}`",
        inline=True,
    )

    embed.add_field(
        name="Max Price/Item",
        value=f"`{current_config.get('max_price_per_item', 50000):,}` R$",
        inline=True,
    )

    embed.add_field(
        name="Total Budget",
        value=f"`{current_config.get('total_budget', 500000):,}` R$",
        inline=True,
    )

    embed.add_field(
        name="Poll Interval",
        value=f"`{current_config.get('poll_interval', 60)}`s",
        inline=True,
    )

    return embed


def build_error_embed(title: str, message: str) -> discord.Embed:
    """Build an error embed."""
    return discord.Embed(
        title=f"Error: {title}",
        description=message,
        color=COLORS["error"],
        timestamp=datetime.utcnow(),
    )


def build_success_embed(title: str, message: str) -> discord.Embed:
    """Build a success embed."""
    return discord.Embed(
        title=title,
        description=message,
        color=COLORS["success"],
        timestamp=datetime.utcnow(),
    )
