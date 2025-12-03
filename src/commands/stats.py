"""Stats commands: /stats overview|purchases|best|worst."""

from __future__ import annotations

import discord
from discord import app_commands

from src.data.models import PortfolioStats
from src.utils.embeds import build_stats_embed, build_error_embed


def setup_stats_commands(bot) -> None:
    """Set up /stats commands on the bot."""

    stats_group = app_commands.Group(name="stats", description="View sniper statistics")

    @stats_group.command(name="overview", description="View portfolio overview")
    async def stats_overview(interaction: discord.Interaction) -> None:
        """Show portfolio overview."""
        await interaction.response.defer()

        if not bot.engine:
            await interaction.followup.send(
                embed=build_error_embed("Error", "Engine not initialized"),
            )
            return

        # Calculate stats from engine
        status = bot.engine.get_status()
        engine_stats = status.get("stats", {})

        # Create portfolio stats
        portfolio = PortfolioStats(
            total_spent=engine_stats.get("total_spent", 0),
            current_value=engine_stats.get("total_spent", 0),  # Would need to track actual current values
            unrealized_pnl=0,  # Would need periodic value updates
            realized_pnl=0,
            total_purchases=engine_stats.get("purchases_attempted", 0),
            successful_purchases=engine_stats.get("purchases_successful", 0),
            failed_purchases=engine_stats.get("purchases_attempted", 0) - engine_stats.get("purchases_successful", 0),
            winning_trades=0,  # Would need to track
            losing_trades=0,
        )

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
        """Show recent purchases."""
        await interaction.response.defer()

        # This would require storing purchase records
        embed = discord.Embed(
            title="Recent Purchases",
            description="Purchase tracking coming soon!",
            color=discord.Color.blue(),
        )

        await interaction.followup.send(embed=embed)

    @stats_group.command(name="best", description="View best performing snipes")
    async def stats_best(interaction: discord.Interaction) -> None:
        """Show best snipes."""
        embed = discord.Embed(
            title="Best Snipes",
            description="Performance tracking coming soon!",
            color=discord.Color.green(),
        )

        await interaction.response.send_message(embed=embed)

    @stats_group.command(name="worst", description="View worst performing snipes")
    async def stats_worst(interaction: discord.Interaction) -> None:
        """Show worst snipes."""
        embed = discord.Embed(
            title="Worst Snipes",
            description="Performance tracking coming soon!",
            color=discord.Color.red(),
        )

        await interaction.response.send_message(embed=embed)

    # Add group to bot
    bot.tree.add_command(stats_group)
