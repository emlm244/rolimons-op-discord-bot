"""Configuration commands: /config mode|strategy|ugc|threshold|info."""

from __future__ import annotations

import discord
from discord import app_commands
from typing import Literal

from src.config import config, PurchaseMode, StrategyFlag, UGCMode, STRATEGY_INFO
from src.utils.embeds import build_config_embed, build_success_embed, build_error_embed


def setup_config_commands(bot) -> None:
    """Set up /config commands on the bot."""

    config_group = app_commands.Group(name="config", description="Sniper configuration commands")

    @config_group.command(name="info", description="Show current configuration")
    async def config_info(interaction: discord.Interaction) -> None:
        """Show current configuration."""
        current = {
            "purchase_mode": config.purchase_mode.value,
            "strategies": [s.value for s in config.strategy_flags],
            "ugc_mode": config.ugc_mode.value,
            "snipe_threshold": config.snipe_threshold,
            "alert_threshold": config.alert_threshold,
            "max_price_per_item": config.max_price_per_item,
            "total_budget": config.total_budget,
            "poll_interval": config.poll_interval_seconds,
        }
        embed = build_config_embed(current)
        await interaction.response.send_message(embed=embed)

    @config_group.command(name="mode", description="Set purchase mode")
    @app_commands.describe(
        mode="The purchase mode to use"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Alert + Confirm (default)", value="alert_confirm"),
        app_commands.Choice(name="Full Auto", value="full_auto"),
        app_commands.Choice(name="Hybrid (auto 85+, confirm 70-84)", value="hybrid"),
    ])
    async def config_mode(
        interaction: discord.Interaction,
        mode: str,
    ) -> None:
        """Set purchase mode."""
        try:
            new_mode = PurchaseMode(mode)
            config.purchase_mode = new_mode

            if bot.engine:
                bot.engine.purchase_mode = new_mode

            descriptions = {
                "alert_confirm": "Bot will alert and wait for confirmation before purchasing.",
                "full_auto": "Bot will automatically purchase items that meet the threshold.",
                "hybrid": "Auto-buy for scores 85+, require confirmation for 70-84.",
            }

            await interaction.response.send_message(
                embed=build_success_embed(
                    "Purchase Mode Updated",
                    f"Mode set to **{mode}**\n\n{descriptions.get(mode, '')}",
                ),
            )
        except ValueError:
            await interaction.response.send_message(
                embed=build_error_embed("Invalid Mode", f"Unknown mode: {mode}"),
                ephemeral=True,
            )

    @config_group.command(name="strategy", description="Set trading strategy")
    @app_commands.describe(
        strategy="The trading strategy to use"
    )
    @app_commands.choices(strategy=[
        app_commands.Choice(name="Quick Flips - Fast resale, smaller margins", value="quick_flips"),
        app_commands.Choice(name="Value Plays - Deep discounts, hold longer", value="value_plays"),
        app_commands.Choice(name="Rare Hunting - Rare items, high risk/reward", value="rare_hunting"),
    ])
    async def config_strategy(
        interaction: discord.Interaction,
        strategy: str,
    ) -> None:
        """Set trading strategy."""
        try:
            new_strategy = StrategyFlag(strategy)
            config.strategy_flags = [new_strategy]

            if bot.engine and bot.engine.scorer:
                bot.engine.scorer.strategies = [new_strategy]

            info = STRATEGY_INFO.get(new_strategy, {})
            await interaction.response.send_message(
                embed=build_success_embed(
                    f"{info.get('emoji', '')} Strategy Updated",
                    f"**{info.get('name', strategy)}**\n\n"
                    f"{info.get('description', '')}\n\n"
                    f"*Effect: {info.get('effect', '')}*",
                ),
            )
        except ValueError:
            await interaction.response.send_message(
                embed=build_error_embed("Invalid Strategy", f"Unknown strategy: {strategy}"),
                ephemeral=True,
            )

    @config_group.command(name="ugc", description="Set UGC item handling")
    @app_commands.describe(
        mode="How to handle UGC limited items"
    )
    @app_commands.choices(mode=[
        app_commands.Choice(name="Include with penalty (-10 score)", value="include"),
        app_commands.Choice(name="Exclude completely", value="exclude"),
    ])
    async def config_ugc(
        interaction: discord.Interaction,
        mode: str,
    ) -> None:
        """Set UGC handling mode."""
        try:
            new_mode = UGCMode(mode)
            config.ugc_mode = new_mode

            if bot.engine:
                if bot.engine.pre_filter:
                    bot.engine.pre_filter.ugc_mode = new_mode
                if bot.engine.scorer:
                    bot.engine.scorer.ugc_mode = new_mode

            descriptions = {
                "include": "UGC items will be considered but receive a -10 score penalty due to higher risk.",
                "exclude": "UGC items will be completely ignored. Only classic Roblox limiteds will be sniped.",
            }

            await interaction.response.send_message(
                embed=build_success_embed(
                    "UGC Mode Updated",
                    f"Mode set to **{mode}**\n\n{descriptions.get(mode, '')}",
                ),
            )
        except ValueError:
            await interaction.response.send_message(
                embed=build_error_embed("Invalid Mode", f"Unknown mode: {mode}"),
                ephemeral=True,
            )

    @config_group.command(name="threshold", description="Set minimum snipe score threshold")
    @app_commands.describe(
        value="Minimum score to trigger snipe (0-100, default: 70)"
    )
    async def config_threshold(
        interaction: discord.Interaction,
        value: int,
    ) -> None:
        """Set snipe threshold."""
        if not 0 <= value <= 100:
            await interaction.response.send_message(
                embed=build_error_embed("Invalid Value", "Threshold must be between 0 and 100"),
                ephemeral=True,
            )
            return

        config.snipe_threshold = value

        tier_msg = ""
        if value >= 85:
            tier_msg = "Only EXCELLENT tier snipes will trigger."
        elif value >= 70:
            tier_msg = "GOOD and EXCELLENT tier snipes will trigger."
        elif value >= 50:
            tier_msg = "RISKY, GOOD, and EXCELLENT tier snipes will trigger."
        else:
            tier_msg = "Warning: Low threshold may result in poor snipes."

        await interaction.response.send_message(
            embed=build_success_embed(
                "Threshold Updated",
                f"Snipe threshold set to **{value}**\n\n{tier_msg}",
            ),
        )

    @config_group.command(name="budget", description="Set maximum price per item")
    @app_commands.describe(
        robux="Maximum Robux to spend per item"
    )
    async def config_budget(
        interaction: discord.Interaction,
        robux: int,
    ) -> None:
        """Set max price per item."""
        if robux < 0:
            await interaction.response.send_message(
                embed=build_error_embed("Invalid Value", "Budget must be positive"),
                ephemeral=True,
            )
            return

        config.max_price_per_item = robux

        if bot.engine and bot.engine.pre_filter:
            bot.engine.pre_filter.max_price = robux

        await interaction.response.send_message(
            embed=build_success_embed(
                "Budget Updated",
                f"Maximum price per item set to **{robux:,} R$**",
            ),
        )

    @config_group.command(name="total_budget", description="Set total session budget")
    @app_commands.describe(
        robux="Total Robux budget for this session"
    )
    async def config_total_budget(
        interaction: discord.Interaction,
        robux: int,
    ) -> None:
        """Set total budget."""
        if robux < 0:
            await interaction.response.send_message(
                embed=build_error_embed("Invalid Value", "Budget must be positive"),
                ephemeral=True,
            )
            return

        config.total_budget = robux

        await interaction.response.send_message(
            embed=build_success_embed(
                "Total Budget Updated",
                f"Total session budget set to **{robux:,} R$**",
            ),
        )

    # Strategy info command with button
    @config_group.command(name="strategies", description="View all strategy options with details")
    async def config_strategies(interaction: discord.Interaction) -> None:
        """Show strategy information."""
        embed = discord.Embed(
            title="Trading Strategies",
            description="Choose a strategy that matches your trading style. Each strategy modifies how the algorithm scores opportunities.",
            color=discord.Color.blue(),
        )

        for flag, info in STRATEGY_INFO.items():
            embed.add_field(
                name=f"{info['emoji']} {info['name']}",
                value=f"{info['description']}\n\n*Effect: {info['effect']}*",
                inline=False,
            )

        embed.set_footer(text="Use /config strategy <name> to set your strategy")

        await interaction.response.send_message(embed=embed)

    # Add group to bot
    bot.tree.add_command(config_group)
