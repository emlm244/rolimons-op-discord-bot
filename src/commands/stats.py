"""Stats commands: /stats overview|purchases|best|worst."""

from __future__ import annotations

import discord
from discord import app_commands
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from src.data.models import PortfolioStats, PurchaseRecord
from src.utils.embeds import build_stats_embed, build_error_embed

if TYPE_CHECKING:
    from src.bot import RISniperBot


def setup_stats_commands(bot: "RISniperBot") -> None:
    """Set up /stats commands on the bot."""

    stats_group = app_commands.Group(name="stats", description="View sniper statistics")

    @stats_group.command(name="overview", description="View portfolio overview")
    async def stats_overview(interaction: discord.Interaction) -> None:
        """Show portfolio overview with real P&L data."""
        await interaction.response.defer()

        if not bot.tracker:
            await interaction.followup.send(
                embed=build_error_embed("Error", "Analytics tracker not initialized"),
            )
            return

        # Get real stats from tracker
        portfolio = bot.tracker.get_portfolio_stats()
        embed = build_stats_embed(portfolio)
        await interaction.followup.send(embed=embed)

    @stats_group.command(name="session", description="View current session stats")
    async def stats_session(interaction: discord.Interaction) -> None:
        """Show session stats."""
        if not bot.engine:
            await interaction.response.send_message(
                embed=build_error_embed("Error", "Engine not initialized"),
                ephemeral=True,
            )
            return

        status = bot.engine.get_status()
        stats = status.get("stats", {})

        embed = discord.Embed(
            title="Session Statistics",
            color=discord.Color.blue(),
        )

        # Session info
        if stats.get("started_at"):
            embed.add_field(
                name="Started",
                value=stats["started_at"][:19].replace("T", " "),
                inline=True,
            )

        embed.add_field(
            name="Items Scanned",
            value=f"{stats.get('items_scanned', 0):,}",
            inline=True,
        )

        embed.add_field(
            name="Filtered",
            value=f"{stats.get('items_filtered', 0):,}",
            inline=True,
        )

        embed.add_field(
            name="Scored",
            value=f"{stats.get('items_scored', 0):,}",
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

        await interaction.response.send_message(embed=embed)

    @stats_group.command(name="purchases", description="View recent purchases")
    async def stats_purchases(interaction: discord.Interaction) -> None:
        """Show recent purchases from tracker."""
        await interaction.response.defer()

        if not bot.tracker:
            await interaction.followup.send(
                embed=build_error_embed("Error", "Analytics tracker not initialized"),
            )
            return

        purchases = bot.tracker.get_all_purchases()

        if not purchases:
            embed = discord.Embed(
                title="Recent Purchases",
                description="No purchases recorded yet.",
                color=discord.Color.blue(),
            )
            await interaction.followup.send(embed=embed)
            return

        # Show last 10 purchases
        recent = sorted(purchases, key=lambda p: p.purchase_time, reverse=True)[:10]

        embed = discord.Embed(
            title="Recent Purchases",
            description=f"Showing {len(recent)} of {len(purchases)} total purchases",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc),
        )

        for record in recent:
            status_emoji = "" if record.success else ""
            pnl = record.unrealized_pnl
            pnl_emoji = "" if pnl >= 0 else ""

            value = (
                f"**Price:** {record.purchase_price:,} R$\n"
                f"**Current Value:** {record.current_value:,} R$\n"
                f"**P&L:** {pnl_emoji} {pnl:+,} R$ ({record.unrealized_pnl_percent:+.1f}%)\n"
                f"**Score:** {record.snipe_score}/100"
            )

            embed.add_field(
                name=f"{status_emoji} {record.item_name}",
                value=value,
                inline=True,
            )

        await interaction.followup.send(embed=embed)

    @stats_group.command(name="best", description="View best performing snipes")
    async def stats_best(interaction: discord.Interaction) -> None:
        """Show best snipes from tracker."""
        await interaction.response.defer()

        if not bot.tracker:
            await interaction.followup.send(
                embed=build_error_embed("Error", "Analytics tracker not initialized"),
            )
            return

        best_snipes = bot.tracker.get_best_snipes(limit=5)

        if not best_snipes:
            embed = discord.Embed(
                title="Best Snipes",
                description="No successful purchases to show yet.",
                color=discord.Color.green(),
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="Best Snipes",
            description="Top 5 most profitable snipes",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )

        for i, record in enumerate(best_snipes, 1):
            pnl = record.unrealized_pnl

            value = (
                f"**Bought:** {record.purchase_price:,} R$\n"
                f"**Now Worth:** {record.current_value:,} R$\n"
                f"**Profit:** +{pnl:,} R$ ({record.unrealized_pnl_percent:+.1f}%)\n"
                f"**Score:** {record.snipe_score}/100"
            )

            embed.add_field(
                name=f"#{i} {record.item_name}",
                value=value,
                inline=False,
            )

        await interaction.followup.send(embed=embed)

    @stats_group.command(name="worst", description="View worst performing snipes")
    async def stats_worst(interaction: discord.Interaction) -> None:
        """Show worst snipes from tracker."""
        await interaction.response.defer()

        if not bot.tracker:
            await interaction.followup.send(
                embed=build_error_embed("Error", "Analytics tracker not initialized"),
            )
            return

        worst_snipes = bot.tracker.get_worst_snipes(limit=5)

        if not worst_snipes:
            embed = discord.Embed(
                title="Worst Snipes",
                description="No purchases to analyze yet.",
                color=discord.Color.red(),
            )
            await interaction.followup.send(embed=embed)
            return

        embed = discord.Embed(
            title="Worst Snipes",
            description="Bottom 5 performing snipes",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )

        for i, record in enumerate(worst_snipes, 1):
            pnl = record.unrealized_pnl
            pnl_emoji = "" if pnl >= 0 else ""

            value = (
                f"**Bought:** {record.purchase_price:,} R$\n"
                f"**Now Worth:** {record.current_value:,} R$\n"
                f"**P&L:** {pnl_emoji} {pnl:+,} R$ ({record.unrealized_pnl_percent:+.1f}%)\n"
                f"**Score:** {record.snipe_score}/100"
            )

            embed.add_field(
                name=f"#{i} {record.item_name}",
                value=value,
                inline=False,
            )

        await interaction.followup.send(embed=embed)

    # Add group to bot
    bot.tree.add_command(stats_group)
