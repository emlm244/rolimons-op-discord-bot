"""Analyze command: /analyze <item_id> [price]."""

from __future__ import annotations

import discord
from discord import app_commands
from typing import Optional

from src.utils.embeds import build_analyze_embed, build_error_embed


def setup_analyze_commands(bot) -> None:
    """Set up /analyze command on the bot."""

    @bot.tree.command(name="analyze", description="Analyze an item's snipe potential")
    @app_commands.describe(
        item_id="The Roblox item ID to analyze",
        price="Optional: Price to analyze at (uses lowest reseller if not provided)",
    )
    async def analyze(
        interaction: discord.Interaction,
        item_id: int,
        price: Optional[int] = None,
    ) -> None:
        """Analyze an item's snipe score."""
        await interaction.response.defer()

        if not bot.engine:
            await interaction.followup.send(
                embed=build_error_embed("Error", "Engine not initialized"),
            )
            return

        # Get item data
        item = await bot.engine.rolimons.get_item(item_id)
        if not item:
            await interaction.followup.send(
                embed=build_error_embed(
                    "Item Not Found",
                    f"Could not find item with ID `{item_id}` in Rolimons database.",
                ),
            )
            return

        # Get price if not provided
        if price is None:
            listings = await bot.engine.roblox.get_resellers(item_id, limit=1)
            if listings:
                price = listings[0].price
            else:
                # Use value as fallback
                price = item.value

        if price <= 0:
            await interaction.followup.send(
                embed=build_error_embed(
                    "Invalid Price",
                    "Could not determine price. Please provide a price manually.",
                ),
            )
            return

        # First check pre-filter
        filter_result = bot.engine.pre_filter.filter(item, price)
        if not filter_result.passed:
            # Still score it but show the filter rejection
            embed = discord.Embed(
                title=f"Analysis: {item.name}",
                description=f"**PRE-FILTER REJECTED**\n\nReason: {filter_result.reason.description}",
                color=discord.Color.red(),
            )
            embed.add_field(name="Item ID", value=str(item_id), inline=True)
            embed.add_field(name="Price", value=f"{price:,} R$", inline=True)
            embed.add_field(name="Value", value=f"{item.value:,} R$", inline=True)

            if item.projected:
                embed.add_field(
                    name="Warning",
                    value="This item is marked as **PROJECTED** - artificially inflated RAP. Avoid!",
                    inline=False,
                )

            embed.set_thumbnail(url=item.thumbnail_url)
            await interaction.followup.send(embed=embed)
            return

        # Score the item
        result = bot.engine.scorer.score(item, price)

        # Build and send embed
        embed = build_analyze_embed(result)

        # Add links
        embed.add_field(
            name="Links",
            value=f"[Rolimons]({item.rolimons_url}) | [Roblox]({item.roblox_url})",
            inline=False,
        )

        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="lookup", description="Quick lookup of item info")
    @app_commands.describe(
        item_id="The Roblox item ID to look up",
    )
    async def lookup(
        interaction: discord.Interaction,
        item_id: int,
    ) -> None:
        """Quick item lookup without scoring."""
        await interaction.response.defer()

        if not bot.engine:
            await interaction.followup.send(
                embed=build_error_embed("Error", "Engine not initialized"),
            )
            return

        # Get item data
        item = await bot.engine.rolimons.get_item(item_id)
        if not item:
            await interaction.followup.send(
                embed=build_error_embed(
                    "Item Not Found",
                    f"Could not find item with ID `{item_id}` in Rolimons database.",
                ),
            )
            return

        # Get current listings
        listings = await bot.engine.roblox.get_resellers(item_id, limit=5)

        embed = discord.Embed(
            title=item.name,
            url=item.rolimons_url,
            color=discord.Color.blue(),
        )

        embed.add_field(name="Value", value=f"{item.value:,} R$", inline=True)
        embed.add_field(name="RAP", value=f"{item.rap:,} R$", inline=True)
        embed.add_field(name="Type", value=item.item_type, inline=True)

        embed.add_field(name="Demand", value=item.display_demand, inline=True)
        embed.add_field(name="Trend", value=item.display_trend, inline=True)

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

        # Current listings
        if listings:
            listing_text = "\n".join(
                f"{i+1}. {l.price:,} R$ - {l.seller_name}"
                for i, l in enumerate(listings[:5])
            )
            embed.add_field(
                name="Current Listings",
                value=f"```{listing_text}```",
                inline=False,
            )
        else:
            embed.add_field(
                name="Current Listings",
                value="No listings available",
                inline=False,
            )

        embed.set_thumbnail(url=item.thumbnail_url)
        embed.set_footer(text=f"Item ID: {item_id}")

        await interaction.followup.send(embed=embed)
